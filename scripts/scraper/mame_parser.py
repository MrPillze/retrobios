"""Parser for MAME C source files.

Extracts BIOS root sets and ROM definitions from MAME driver sources.
Handles GAME/SYST/COMP/CONS macros with MACHINE_IS_BIOS_ROOT flag,
ROM_START/ROM_END blocks, ROM_LOAD variants, ROM_REGION, ROM_SYSTEM_BIOS,
NO_DUMP filtering, and BAD_DUMP flagging.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Macros that declare a machine entry
_MACHINE_MACROS = re.compile(
    r'\b(GAME|SYST|COMP|CONS)\s*\(',
    re.MULTILINE,
)

# ROM block boundaries
_ROM_START = re.compile(r'ROM_START\s*\(\s*(\w+)\s*\)')
_ROM_END = re.compile(r'ROM_END')

# ROM_REGION( tag, offset, size )
_ROM_REGION = re.compile(
    r'ROM_REGION\s*\('
    r'\s*(0x[\da-fA-F]+|\d+)\s*,'   # size
    r'\s*"([^"]+)"\s*,',            # tag
)

# ROM_SYSTEM_BIOS( index, label, description )
_ROM_SYSTEM_BIOS = re.compile(
    r'ROM_SYSTEM_BIOS\s*\('
    r'\s*(\d+)\s*,'           # index
    r'\s*"([^"]+)"\s*,'       # label
    r'\s*"([^"]+)"\s*\)',     # description
)

# All ROM_LOAD variants: ROM_LOAD, ROMX_LOAD, ROM_LOAD16_BYTE, ROM_LOAD16_WORD, etc.
_ROM_LOAD = re.compile(
    r'(ROMX?_LOAD(?:16_BYTE|16_WORD|16_WORD_SWAP|32_BYTE|32_WORD|32_WORD_SWAP)?)\s*\('
    r'\s*"([^"]+)"\s*,'               # name
    r'\s*(0x[\da-fA-F]+|\d+)\s*,'     # offset
    r'\s*(0x[\da-fA-F]+|\d+)\s*,',    # size
)

# CRC32 and SHA1 within a ROM_LOAD line
_CRC_SHA = re.compile(
    r'CRC\s*\(\s*([0-9a-fA-F]+)\s*\)'
    r'\s+'
    r'SHA1\s*\(\s*([0-9a-fA-F]+)\s*\)',
)

_NO_DUMP = re.compile(r'\bNO_DUMP\b')
_BAD_DUMP = re.compile(r'\bBAD_DUMP\b')
_ROM_BIOS = re.compile(r'ROM_BIOS\s*\(\s*(\d+)\s*\)')


def find_bios_root_sets(source: str, filename: str) -> dict[str, dict]:
    """Find machine entries flagged as BIOS root sets.

    Scans for GAME/SYST/COMP/CONS macros where the args include
    MACHINE_IS_BIOS_ROOT, returns set names with source location.
    """
    results: dict[str, dict] = {}

    for match in _MACHINE_MACROS.finditer(source):
        start = match.end() - 1  # position of opening paren
        block_end = _find_closing_paren(source, start)
        if block_end == -1:
            continue

        block = source[start:block_end + 1]
        if 'MACHINE_IS_BIOS_ROOT' not in block:
            continue

        # Extract set name: first arg after the opening paren
        inner = block[1:]  # skip opening paren
        args = _split_macro_args(inner)
        if not args:
            continue

        # The set name position varies by macro type
        # GAME(year, setname, parent, machine, input, init, monitor, company, fullname, flags)
        # CONS(year, setname, parent, compat, machine, input, init, company, fullname, flags)
        # COMP(year, setname, parent, compat, machine, input, init, company, fullname, flags)
        # SYST(year, setname, parent, compat, machine, input, init, company, fullname, flags)
        # In all cases, setname is the second arg (index 1)
        if len(args) < 2:
            continue

        set_name = args[1].strip()
        line_no = source[:match.start()].count('\n') + 1

        results[set_name] = {
            'source_file': filename,
            'source_line': line_no,
        }

    return results


def parse_rom_block(source: str, set_name: str) -> list[dict]:
    """Parse ROM definitions for a given set name.

    Finds the ROM_START(set_name)...ROM_END block and extracts all
    ROM_LOAD entries with their metadata. Skips NO_DUMP entries,
    flags BAD_DUMP entries.
    """
    pattern = re.compile(
        r'ROM_START\s*\(\s*' + re.escape(set_name) + r'\s*\)',
    )
    start_match = pattern.search(source)
    if not start_match:
        return []

    end_match = _ROM_END.search(source, start_match.end())
    if not end_match:
        return []

    block = source[start_match.end():end_match.start()]
    return _parse_rom_entries(block)


def parse_mame_source_tree(base_path: str) -> dict[str, dict]:
    """Walk MAME source tree and extract all BIOS root sets with ROMs.

    Scans src/mame/ and src/devices/ for C/C++ source files.
    """
    results: dict[str, dict] = {}
    root = Path(base_path)

    search_dirs = [root / 'src' / 'mame', root / 'src' / 'devices']

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for dirpath, _dirnames, filenames in os.walk(search_dir):
            for fname in filenames:
                if not fname.endswith(('.cpp', '.c', '.h', '.hxx')):
                    continue
                filepath = Path(dirpath) / fname
                rel_path = str(filepath.relative_to(root))
                content = filepath.read_text(encoding='utf-8', errors='replace')

                bios_sets = find_bios_root_sets(content, rel_path)
                for set_name, info in bios_sets.items():
                    roms = parse_rom_block(content, set_name)
                    results[set_name] = {
                        'source_file': info['source_file'],
                        'source_line': info['source_line'],
                        'roms': roms,
                    }

    return results


def _find_closing_paren(source: str, start: int) -> int:
    """Find the matching closing paren for source[start] which must be '('."""
    depth = 0
    i = start
    while i < len(source):
        ch = source[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i
        elif ch == '"':
            i += 1
            while i < len(source) and source[i] != '"':
                i += 1
        i += 1
    return -1


def _split_macro_args(inner: str) -> list[str]:
    """Split macro arguments respecting nested parens and strings."""
    args: list[str] = []
    depth = 0
    current: list[str] = []

    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == '"':
            current.append(ch)
            i += 1
            while i < len(inner) and inner[i] != '"':
                current.append(inner[i])
                i += 1
            if i < len(inner):
                current.append(inner[i])
        elif ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            if depth == 0:
                args.append(''.join(current))
                break
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current))
            current = []
        else:
            current.append(ch)
        i += 1

    if current:
        remaining = ''.join(current).strip()
        if remaining:
            args.append(remaining)

    return args


def _parse_rom_entries(block: str) -> list[dict]:
    """Parse ROM entries from a ROM block (content between ROM_START and ROM_END)."""
    roms: list[dict] = []
    current_region = ''
    bios_labels: dict[int, tuple[str, str]] = {}  # index -> (label, description)

    for line in block.split('\n'):
        stripped = line.strip()

        # Track region changes
        region_match = _ROM_REGION.search(stripped)
        if region_match:
            current_region = region_match.group(2)
            continue

        # Track BIOS labels
        bios_match = _ROM_SYSTEM_BIOS.search(stripped)
        if bios_match:
            idx = int(bios_match.group(1))
            bios_labels[idx] = (bios_match.group(2), bios_match.group(3))
            continue

        # ROM_LOAD variants
        load_match = _ROM_LOAD.search(stripped)
        if not load_match:
            continue

        # Skip NO_DUMP
        if _NO_DUMP.search(stripped):
            continue

        rom_name = load_match.group(2)
        rom_size = _parse_int(load_match.group(4))

        # Extract CRC32 and SHA1
        crc_sha_match = _CRC_SHA.search(stripped)
        crc32 = ''
        sha1 = ''
        if crc_sha_match:
            crc32 = crc_sha_match.group(1).lower()
            sha1 = crc_sha_match.group(2).lower()

        bad_dump = bool(_BAD_DUMP.search(stripped))

        # Check for ROM_BIOS association
        bios_index = None
        bios_label = ''
        bios_description = ''
        bios_ref = _ROM_BIOS.search(stripped)
        if bios_ref:
            bios_index = int(bios_ref.group(1))
            if bios_index in bios_labels:
                bios_label, bios_description = bios_labels[bios_index]

        entry: dict = {
            'name': rom_name,
            'size': rom_size,
            'crc32': crc32,
            'sha1': sha1,
            'region': current_region,
            'bad_dump': bad_dump,
        }

        if bios_index is not None:
            entry['bios_index'] = bios_index
            entry['bios_label'] = bios_label
            entry['bios_description'] = bios_description

        roms.append(entry)

    return roms


def _parse_int(value: str) -> int:
    """Parse an integer that may be hex (0x...) or decimal."""
    value = value.strip()
    if value.startswith('0x') or value.startswith('0X'):
        return int(value, 16)
    return int(value)

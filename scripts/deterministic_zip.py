"""Deterministic ZIP builder for MAME BIOS archives.

Creates byte-identical ZIP files from individual ROM atoms, enabling:
- Reproducible builds: same ROMs -> same ZIP hash, always
- Version-agnostic assembly: build neogeo.zip for any MAME version
- Deduplication: store ROM atoms once, assemble any ZIP on demand

A ZIP's hash depends on: file content, filenames, order, timestamps,
compression, and permissions. This module fixes all metadata to produce
deterministic output.

Usage:
    from deterministic_zip import build_deterministic_zip, extract_atoms

    # Extract atoms from an existing ZIP
    atoms = extract_atoms("neogeo.zip")

    # Build a ZIP from a recipe
    recipe = [
        {"name": "sp-s2.sp1", "crc32": "9036d879"},
        {"name": "000-lo.lo", "crc32": "5a86cff2"},
    ]
    build_deterministic_zip("neogeo.zip", recipe, atom_store)
"""

from __future__ import annotations

import hashlib
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

# Fixed metadata for deterministic ZIPs
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)  # minimum ZIP timestamp
_FIXED_CREATE_SYSTEM = 0  # FAT/DOS (most compatible)
_FIXED_EXTERNAL_ATTR = 0o100644 << 16  # -rw-r--r--
_COMPRESS_LEVEL = 9  # deflate level 9 for determinism


def build_deterministic_zip(
    output_path: str | Path,
    recipe: list[dict],
    atom_store: dict[str, bytes],
    compression: int = zipfile.ZIP_DEFLATED,
) -> str:
    """Build a deterministic ZIP from a recipe and atom store.

    Args:
        output_path: Path for the output ZIP file.
        recipe: List of dicts with 'name' and 'crc32' (lowercase hex, no 0x).
            Files are sorted by name for determinism.
        atom_store: Dict mapping CRC32 (lowercase hex) to ROM binary data.
        compression: ZIP_DEFLATED (default) or ZIP_STORED.

    Returns:
        SHA1 hex digest of the generated ZIP.

    Raises:
        KeyError: If a recipe CRC32 is not found in the atom store.
        ValueError: If a ROM's actual CRC32 doesn't match the recipe.
    """
    # Sort by filename for deterministic order
    sorted_recipe = sorted(recipe, key=lambda r: r["name"])

    with zipfile.ZipFile(
        str(output_path), "w", compression, compresslevel=_COMPRESS_LEVEL
    ) as zf:
        for entry in sorted_recipe:
            name = entry["name"]
            expected_crc = entry.get("crc32", "").lower()

            if expected_crc not in atom_store:
                raise KeyError(
                    f"ROM atom not found: {name} (crc32={expected_crc}). "
                    f"Available: {len(atom_store)} atoms"
                )

            data = atom_store[expected_crc]

            # Verify CRC32 of the atom data
            actual_crc = format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
            if expected_crc and actual_crc != expected_crc:
                raise ValueError(
                    f"CRC32 mismatch for {name}: expected {expected_crc}, got {actual_crc}"
                )

            # Create ZipInfo with fixed metadata
            info = zipfile.ZipInfo(filename=name, date_time=_FIXED_DATE_TIME)
            info.compress_type = compression
            info.create_system = _FIXED_CREATE_SYSTEM
            info.external_attr = _FIXED_EXTERNAL_ATTR

            zf.writestr(info, data)

    # Compute and return the ZIP's SHA1
    sha1 = hashlib.sha1()
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


def extract_atoms(zip_path: str | Path) -> dict[str, bytes]:
    """Extract all ROM atoms from a ZIP, indexed by CRC32.

    Returns: Dict mapping CRC32 (lowercase hex) to raw ROM data.
    """
    atoms: dict[str, bytes] = {}
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            data = zf.read(info.filename)
            crc = format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
            atoms[crc] = data
    return atoms


def extract_atoms_with_names(zip_path: str | Path) -> list[dict]:
    """Extract atoms with full metadata from a ZIP.

    Returns: List of dicts with 'name', 'crc32', 'size', 'data'.
    """
    result = []
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            if info.is_dir():
                continue
            data = zf.read(info.filename)
            crc = format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
            result.append(
                {
                    "name": info.filename,
                    "crc32": crc,
                    "size": len(data),
                    "data": data,
                }
            )
    return result


def verify_zip_determinism(zip_path: str | Path) -> tuple[bool, str, str]:
    """Verify a ZIP can be rebuilt deterministically.

    Extracts atoms, rebuilds the ZIP, compares hashes.

    Returns: (is_deterministic, original_sha1, rebuilt_sha1)
    """
    # Hash the original
    orig_sha1 = hashlib.sha1(Path(zip_path).read_bytes()).hexdigest()

    # Extract atoms
    atoms_list = extract_atoms_with_names(zip_path)
    atom_store = {a["crc32"]: a["data"] for a in atoms_list}
    recipe = [{"name": a["name"], "crc32": a["crc32"]} for a in atoms_list]

    # Rebuild to memory
    buf = BytesIO()
    sorted_recipe = sorted(recipe, key=lambda r: r["name"])
    with zipfile.ZipFile(
        buf, "w", zipfile.ZIP_DEFLATED, compresslevel=_COMPRESS_LEVEL
    ) as zf:
        for entry in sorted_recipe:
            info = zipfile.ZipInfo(filename=entry["name"], date_time=_FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = _FIXED_CREATE_SYSTEM
            info.external_attr = _FIXED_EXTERNAL_ATTR
            zf.writestr(info, atom_store[entry["crc32"]])

    rebuilt_sha1 = hashlib.sha1(buf.getvalue()).hexdigest()
    return orig_sha1 == rebuilt_sha1, orig_sha1, rebuilt_sha1


def rebuild_zip_deterministic(
    source_zip: str | Path,
    output_zip: str | Path,
) -> str:
    """Rebuild an existing ZIP deterministically.

    Extracts all files, reassembles with fixed metadata.
    Returns the SHA1 of the new ZIP.
    """
    atoms_list = extract_atoms_with_names(source_zip)
    atom_store = {a["crc32"]: a["data"] for a in atoms_list}
    recipe = [{"name": a["name"], "crc32": a["crc32"]} for a in atoms_list]
    return build_deterministic_zip(output_zip, recipe, atom_store)


def build_atom_store_from_zips(zip_dir: str | Path) -> dict[str, bytes]:
    """Build a global atom store from all ZIPs in a directory.

    Scans all .zip files, extracts every ROM, indexes by CRC32.
    Identical ROMs (same CRC32) from different ZIPs are stored once.
    """
    store: dict[str, bytes] = {}
    for zip_path in sorted(Path(zip_dir).rglob("*.zip")):
        try:
            atoms = extract_atoms(zip_path)
            store.update(atoms)
        except zipfile.BadZipFile:
            continue
    return store

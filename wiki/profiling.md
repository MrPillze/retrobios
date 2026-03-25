# Profiling guide - RetroBIOS

How to create an emulator profile from source code.

## Approach

A profile documents what an emulator loads at runtime.
The source code is the reference because it reflects actual behavior.
Documentation, .info files, and wikis are useful starting points
but are verified against the code.

## Steps

### 1. Find the source code

Check these locations in order:

1. Upstream original (the emulator's own repository)
2. Libretro fork (may have adapted paths or added files)
3. If not on GitHub: GitLab, Codeberg, SourceForge, archive.org

Always clone both upstream and libretro port to compare.

### 2. Trace file loading

Read the code flow. Don't grep keywords by assumption.
Each emulator has its own way of loading files.

Look for:

- `fopen`, `open`, `read_file`, `load_rom`, `load_bios` calls
- `retro_system_directory` / `system_dir` in libretro cores
- File existence checks (`path_is_valid`, `file_exists`)
- Hash validation (MD5, CRC32, SHA1 comparisons in code)
- Size validation (`fseek`/`ftell`, `stat`, fixed buffer sizes)

### 3. Determine required vs optional

This is decided by code behavior, not by judgment:

- **required**: the core does not start or function without the file
- **optional**: the core works with degraded functionality without it
- **hle_fallback: true**: the core has a high-level emulation path when the file is missing

### 4. Document divergences

When the libretro port differs from the upstream:

- `mode: libretro` - file only used by the libretro core
- `mode: standalone` - file only used in standalone mode
- `mode: both` - used by both (default, can be omitted)

Path differences (current dir vs system_dir) are normal adaptation,
not a divergence. Name changes (e.g. `naomi2_` to `n2_`) may be intentional
to avoid conflicts in the shared system directory.

### 5. Write the YAML profile

```yaml
emulator: Dolphin
type: standalone + libretro
core_classification: community_fork
source: https://github.com/libretro/dolphin
upstream: https://github.com/dolphin-emu/dolphin
profiled_date: 2026-03-25
core_version: 5.0-21264
systems:
  - nintendo-gamecube
  - nintendo-wii

files:
  - name: GC/USA/IPL.bin
    system: nintendo-gamecube
    required: false
    hle_fallback: true
    size: 2097152
    validation: [size, adler32]
    known_hash_adler32: 0x4f1f6f5c
    region: north-america
    source_ref: Source/Core/Core/Boot/Boot_BS2Emu.cpp:42
```

### 6. Validate

```bash
python scripts/cross_reference.py --emulator dolphin --json
python scripts/verify.py --emulator dolphin
```

## YAML field reference

### Profile fields

| Field | Required | Description |
|-------|----------|-------------|
| `emulator` | yes | display name |
| `type` | yes | `libretro`, `standalone`, `standalone + libretro`, `alias`, `launcher` |
| `core_classification` | no | `pure_libretro`, `official_port`, `community_fork`, `frozen_snapshot`, `enhanced_fork`, `game_engine`, `embedded_hle`, `alias`, `launcher` |
| `source` | yes | libretro core repository URL |
| `upstream` | no | original emulator repository URL |
| `profiled_date` | yes | date of source analysis |
| `core_version` | yes | version analyzed |
| `systems` | yes | list of system IDs this core handles |
| `cores` | no | list of core names (default: profile filename) |
| `files` | yes | list of file entries |
| `notes` | no | free-form technical notes |
| `exclusion_note` | no | why the profile has no files |
| `data_directories` | no | references to data dirs in `_data_dirs.yml` |

### File entry fields

| Field | Description |
|-------|-------------|
| `name` | filename as the core expects it |
| `required` | true if the core needs this file to function |
| `system` | system ID this file belongs to |
| `size` | expected size in bytes |
| `md5`, `sha1`, `crc32`, `sha256` | expected hashes from source code |
| `validation` | list of checks the code performs: `size`, `crc32`, `md5`, `sha1` |
| `aliases` | alternate filenames for the same file |
| `mode` | `libretro`, `standalone`, or `both` |
| `hle_fallback` | true if a high-level emulation path exists |
| `category` | `bios` (default), `game_data`, `bios_zip` |
| `region` | geographic region (e.g. `north-america`, `japan`) |
| `source_ref` | source file and line number |
| `path` | path relative to system directory |
| `description` | what this file is |
| `note` | additional context |
| `archive` | parent ZIP if this file is inside an archive |
| `contents` | structure of files inside a BIOS ZIP |
| `storage` | `embedded` (default), `external`, `user_provided` |


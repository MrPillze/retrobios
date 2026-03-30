# Getting started - RetroBIOS

## What are BIOS files?

BIOS files are firmware dumps from original console hardware. Emulators need them to boot games for systems that relied on built-in software (PlayStation, Saturn, Dreamcast, etc.). Without the correct BIOS, the emulator either refuses to start the game or falls back to less accurate software emulation.

## Installation

Three ways to get BIOS files in place, from easiest to most manual.

### Option 1: install.py (recommended)

Self-contained Python script, no dependencies beyond Python 3.10+. Auto-detects your platform and BIOS directory.

```bash
python install.py
```

Override detection if needed:

```bash
python install.py --platform retroarch --dest ~/custom/bios
python install.py --check          # verify existing files without downloading
python install.py --list-platforms  # show supported platforms
```

The installer downloads files from GitHub releases, verifies SHA1 checksums, and places them in the correct directory.

### Option 2: download.sh (Linux/macOS)

One-liner for systems with `curl` or `wget`:

```bash
bash scripts/download.sh retroarch ~/RetroArch/system/
bash scripts/download.sh --list  # show available packs
```

### Option 3: manual download

1. Go to the [releases page](https://github.com/Abdess/retrobios/releases)
2. Download the ZIP pack for your platform
3. Extract to the BIOS directory listed below

## BIOS directory by platform

### RetroArch

RetroArch uses the `system_directory` setting in `retroarch.cfg`. Default locations:

| OS | Default path |
|----|-------------|
| Windows | `%APPDATA%\RetroArch\system\` |
| Linux | `~/.config/retroarch/system/` |
| Linux (Flatpak) | `~/.var/app/org.libretro.RetroArch/config/retroarch/system/` |
| macOS | `~/Library/Application Support/RetroArch/system/` |
| Steam Deck | `~/.var/app/org.libretro.RetroArch/config/retroarch/system/` |
| Android | `/storage/emulated/0/RetroArch/system/` |

To check your actual path: open RetroArch, go to **Settings > Directory > System/BIOS**, or look for `system_directory` in `retroarch.cfg`.

### Batocera

```
/userdata/bios/
```

Accessible via network share at `\\BATOCERA\share\bios\` (Windows) or `smb://batocera/share/bios/` (macOS/Linux).

### Recalbox

```
/recalbox/share/bios/
```

Accessible via network share at `\\RECALBOX\share\bios\`.

### RetroBat

```
bios/
```

Relative to the RetroBat installation directory (e.g., `C:\RetroBat\bios\`).

### RetroDECK

```
~/.var/app/net.retrodeck.retrodeck/retrodeck/bios/
```

### EmuDeck

```
Emulation/bios/
```

Located inside your Emulation folder. On Steam Deck, typically `~/Emulation/bios/`.

### Lakka

```
/storage/system/
```

Accessible via SSH or Samba.

### RetroPie

```
~/RetroPie/BIOS/
```

### BizHawk

```
Firmware/
```

Relative to the BizHawk installation directory.

### RomM

BIOS files are managed through the RomM web interface. Check the
[RomM documentation](https://github.com/rommapp/romm) for setup details.

## Verifying your setup

After placing BIOS files, verify that everything is correct:

```bash
python scripts/verify.py --platform retroarch
python scripts/verify.py --platform batocera
python scripts/verify.py --platform recalbox
```

The output shows each expected file with its status: OK, MISSING, or HASH MISMATCH. Platforms that verify by MD5 (Batocera, Recalbox, EmuDeck) will catch wrong versions. RetroArch only checks that files exist.

For a single system:

```bash
python scripts/verify.py --system sony-playstation
```

For a single emulator core:

```bash
python scripts/verify.py --emulator beetle_psx
```

See [Tools](tools.md) for the full CLI reference.

## Next steps

- [FAQ](faq.md) - common questions and troubleshooting
- [Tools](tools.md) - all available scripts and options
- [Architecture](architecture.md) - how the project works internally

# Wiki - RetroBIOS

Technical documentation for the RetroBIOS toolchain.

## For users

- **[Getting started](getting-started.md)** - installation, BIOS directory paths per platform, verification
- **[FAQ](faq.md)** - common questions, troubleshooting, hash explanations

If you just want to download BIOS packs, see the [home page](../README.md).

## Technical reference

- **[Architecture](architecture.md)** - directory structure, data flow, platform inheritance, pack grouping, security, edge cases, CI workflows
- **[Tools](tools.md)** - CLI reference for every script, pipeline usage, scrapers
- **[Advanced usage](advanced-usage.md)** - custom packs, target filtering, truth generation, emulator verification, offline workflow
- **[Verification modes](verification-modes.md)** - how each platform verifies BIOS files, severity matrix, resolution chain
- **[Data model](data-model.md)** - database.json structure, indexes, file resolution order, YAML formats
- **[Troubleshooting](troubleshooting.md)** - diagnosis by symptom: missing BIOS, hash mismatch, pack issues, verify errors

## For contributors

- **[Profiling guide](profiling.md)** - create an emulator profile from source code, YAML field reference
- **[Adding a platform](adding-a-platform.md)** - scraper, registry, YAML config, exporter, target scraper, install detection
- **[Adding a scraper](adding-a-scraper.md)** - plugin architecture, BaseScraper, parsers, target scrapers
- **[Testing guide](testing-guide.md)** - run tests, fixture pattern, how to add tests, CI integration
- **[Release process](release-process.md)** - CI workflows, large files, manual release

See [contributing](../CONTRIBUTING.md) for submission guidelines.

## Glossary

- **BIOS** - firmware burned into console hardware, needed by emulators that rely on original boot code
- **firmware** - system software loaded by a console at boot; used interchangeably with BIOS in this project
- **HLE** - High-Level Emulation; software reimplementation of BIOS functions, avoids needing the original file
- **hash** - fixed-length fingerprint of a file's contents; this project uses MD5, SHA1, SHA256, and CRC32
- **platform** - a distribution that packages emulators (RetroArch, Batocera, Recalbox, EmuDeck, etc.)
- **core** - an emulator packaged as a libretro plugin, loaded by RetroArch or compatible frontends
- **profile** - a YAML file in `emulators/` documenting one core's BIOS requirements, verified against source code
- **system** - a game console or computer being emulated (e.g. sony-playstation, nintendo-gameboy-advance)
- **pack** - a ZIP archive containing all BIOS files needed by a specific platform
- **ground truth** - the emulator's source code, treated as the authoritative reference for BIOS requirements
- **cross-reference** - comparison of emulator profiles against platform configs to find undeclared files
- **scraper** - a script that fetches BIOS requirement data from an upstream source (System.dat, es_bios.xml, etc.)
- **exporter** - a script that converts ground truth data back into a platform's native format
- **target** - a hardware architecture that a platform runs on (e.g. switch, rpi4, x86_64, steamos)
- **variant** - an alternative version of a BIOS file (different revision, region, or dump), stored in `.variants/`
- **required** - a file the core needs to function; determined by source code behavior
- **optional** - a file the core functions without, possibly with reduced accuracy or missing features
- **hle_fallback** - flag on a file indicating the core has an HLE path; absence is downgraded to INFO severity
- **severity** - the urgency of a verification result: OK (verified), INFO (negligible), WARNING (degraded), CRITICAL (broken)

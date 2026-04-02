# Contributing to RetroBIOS

## Add a BIOS file

1. Fork this repository
2. Place the file in `bios/Manufacturer/Console/filename`
3. Variants (alternate hashes): `bios/Manufacturer/Console/.variants/`
4. Create a Pull Request - checksums are verified automatically

## Add a new platform

1. Write a scraper in `scripts/scraper/`
2. Create the platform YAML in `platforms/`
3. Register in `platforms/_registry.yml`
4. Submit a Pull Request

Contributors who add platform support are credited in the README,
on the documentation site, and in the BIOS packs.

## File conventions

- Files >50 MB go in GitHub release assets (`large-files` release)
- RPG Maker and ScummVM directories are excluded from deduplication
- See the [documentation site](https://abdess.github.io/retrobios/) for full details

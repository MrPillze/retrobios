# Contributing to RetroBIOS

## Types of contributions

- **Add a BIOS file** - a great way to get started. Fork, add the file, open a PR.
- **Create an emulator profile** - document what a core actually loads from source code. See the [profiling guide](https://abdess.github.io/retrobios/wiki/profiling/).
- **Add a platform** - integrate a new frontend (scraper + YAML config). See [adding a platform](https://abdess.github.io/retrobios/wiki/adding-a-platform/).
- **Add or fix a scraper** - parse upstream sources for BIOS requirements. See [adding a scraper](https://abdess.github.io/retrobios/wiki/adding-a-scraper/).
- **Fix a bug or improve tooling** - Python scripts in `scripts/`, single dependency (`pyyaml`).

## Local setup

```bash
git clone https://github.com/Abdess/retrobios.git
cd retrobios
pip install pyyaml

# run tests
python -m unittest tests.test_e2e -v

# run full pipeline (DB + verify + packs + consistency check)
python scripts/pipeline.py --offline
```

Requires Python 3.10 or later.

## Adding a BIOS file

1. Place the file in `bios/Manufacturer/Console/filename`.
2. Alternate versions (different hash, same purpose) go in `bios/Manufacturer/Console/.variants/`.
3. Files over 50 MB go as assets on the `large-files` GitHub release (git handles them better that way).
4. RPG Maker and ScummVM directories are excluded from deduplication - please keep their structure as-is.
5. Open a pull request. CI validates checksums automatically and posts a report.

## Commit conventions

Format: `type: description` (50 characters max, lowercase start).

Allowed types: `feat`, `refactor`, `chore`, `docs`, `fix`.

```
feat: add panasonic 3do bios files
docs: update architecture diagram
fix: resolve truncated md5 matching
chore: remove unused test fixtures
refactor: extract hash logic to common.py
```

Keep messages factual. No marketing language, no superfluous adjectives.

## Code and documentation quality

The codebase runs on Python 3.10+ with a single dependency (`pyyaml`). All modules
include `from __future__ import annotations` at the top. Type hints on every function
signature, `pathlib` instead of `os.path`, and dataclasses where a plain class would
just hold attributes.

On performance: O(1) or O(n) algorithms are preferred. If something needs O(n^2), a
comment explaining why helps future readers. List comprehensions over explicit loops,
generators when iterating large datasets, and standard default arguments
(`def f(items=None)` over `def f(items=[])`).

File I/O uses context managers. ZIP extraction goes through `safe_extract_zip()` in
`common.py`, which prevents zip-slip path traversal.

The code stays lean. Comments that describe *why* age better than comments that
restate *what*. Unused variables can be deleted rather than renamed with an underscore.

The same spirit applies to documentation and emulator profiles. Straightforward
language, honest labels ("untested" when something is untested).

When a bug is spotted while working on something else, fixing it in the same PR
keeps things tidy. Features ideally ship complete in one pass: code, tests, a
passing pipeline run, and any documentation updates together.

## Pull request process

CI runs four checks on every PR:

| Check | What it does |
|-------|-------------|
| `validate-bios` | hashes changed BIOS files against the database, posts a validation report |
| `validate-configs` | schema-validates platform YAML configs |
| `run-tests` | runs the full E2E test suite |
| `label-pr` | auto-labels the PR based on changed file paths |

All four checks must pass. One maintainer approval is required before merge.

## Project philosophy

This repository is an archive. The goal is a complete collection of every file a
user needs to run every supported console in an emulator, with zero friction. That
scope goes beyond BIOS ROMs: firmware updates, system fonts, data files, encryption
keys, hiscore databases, anything the emulator loads from disk rather than generating
itself. In a hundred years the pack should still work out of the box.

Licensing considerations are secondary to completeness. If an emulator needs a
file to function, the file belongs in the collection. The project's legal position is
documented in the FAQ section of the site.

Integrity matters. Every file, hash, and metadata field is cross-checked
against the emulator's source code. Upstream references like System.dat,
`.info` files, and wiki pages are valuable and generally accurate, though
they can occasionally fall out of date. When an upstream source and the
code disagree, the code at runtime is the tiebreaker.

## Documentation

Full reference docs, profiling guides, and architecture details are on the [documentation site](https://abdess.github.io/retrobios/).

# Release Process

This page documents the CI/CD pipeline: what each workflow does, how releases
are built, and how to run the process manually.

## CI workflows overview

The project uses 4 GitHub Actions workflows. All use only official GitHub
actions (`actions/checkout`, `actions/setup-python`, `actions/upload-pages-artifact`,
`actions/deploy-pages`). No third-party actions.

Budget target: ~175 minutes/month on the GitHub free tier.

| Workflow | File | Trigger |
|----------|------|---------|
| Build & Release | `build.yml` | Push to `bios/**` or `platforms/**`, manual dispatch |
| Deploy Site | `deploy-site.yml` | Push to main (platforms, emulators, wiki, scripts, database.json, mkdocs.yml), manual |
| PR Validation | `validate.yml` | PR touching `bios/**` or `platforms/**` |
| Weekly Sync | `watch.yml` | Cron Monday 06:00 UTC, manual dispatch |

## build.yml - Build & Release

Currently disabled (`if: false` on the release job) until pack generation is
validated in production.

**Trigger.** Push to `main` on `bios/**` or `platforms/**` paths, or manual
`workflow_dispatch` with optional `force_release` flag to bypass rate limiting.

**Concurrency.** Group `build`, cancel in-progress.

**Steps:**

1. Checkout, Python 3.12, install `pyyaml`
2. Run `test_e2e`
3. Rate limit check: skip if last release was less than 7 days ago (unless
   `force_release` is set)
4. Restore large files from the `large-files` release into `.cache/large/`
5. Refresh data directories (`refresh_data_dirs.py`)
6. Build packs (`generate_pack.py --all --output-dir dist/`)
7. Create GitHub release with tag `v{YYYY.MM.DD}` (appends `.N` suffix if
   a same-day release already exists)
8. Clean up old releases, keeping the 3 most recent plus `large-files`

**Release notes** include file count, total size, per-pack sizes, and the last
15 non-merge commits touching `bios/` or `platforms/`.

## deploy-site.yml - Deploy Documentation Site

**Trigger.** Push to `main` when any of these paths change: `platforms/`,
`emulators/`, `wiki/`, `scripts/generate_site.py`, `scripts/generate_readme.py`,
`scripts/verify.py`, `scripts/common.py`, `database.json`, `mkdocs.yml`.
Also manual dispatch.

**Steps:**

1. Checkout, Python 3.12
2. Install `pyyaml`, `mkdocs-material`, `pymdown-extensions`
3. Run `generate_site.py` (converts YAML data into MkDocs pages)
4. Run `generate_readme.py` (rebuilds README.md and CONTRIBUTING.md)
5. `mkdocs build` to produce the static site
6. Upload artifact, deploy to GitHub Pages

The site is deployed via the `github-pages` environment using the official
`actions/deploy-pages` action.

## validate.yml - PR Validation

**Trigger.** Pull requests that modify `bios/**` or `platforms/**`.

**Concurrency.** Per-PR group, cancel in-progress.

Four parallel jobs:

**validate-bios.** Diffs the PR to find changed BIOS files, runs
`validate_pr.py --markdown` on each, and posts the validation report as a PR
comment (hash verification, database match status).

**validate-configs.** Validates all platform YAML files against
`schemas/platform.schema.json` using `jsonschema`. Fails if any config does
not match the schema.

**run-tests.** Runs `python -m unittest tests.test_e2e -v`. Must pass before
merge.

**label-pr.** Auto-labels the PR based on changed paths:

| Path pattern | Label |
|-------------|-------|
| `bios/` | `bios` |
| `bios/{Manufacturer}/` | `system:{manufacturer}` |
| `platforms/` | `platform-config` |
| `scripts/` | `automation` |

## watch.yml - Weekly Platform Sync

**Trigger.** Cron schedule every Monday at 06:00 UTC, or manual dispatch.

**Flow:**

1. Scrape live upstream sources (System.dat, batocera-systems, es_bios.xml,
   etc.) and regenerate platform YAML configs
2. Auto-fetch missing BIOS files
3. Refresh data directories
4. Run dedup
5. Regenerate `database.json`
6. Create or update a PR with labels `automated` and `platform-update`

The PR contains all changes from the scrape cycle. A maintainer reviews and
merges.

## Large files management

Files larger than 50 MB are stored as assets on a permanent GitHub release
named `large-files` (to keep the git repository lightweight).

Known large files: PS3UPDAT.PUP, PSVUPDAT.PUP, PSP2UPDAT.PUP, dsi_nand.bin,
maclc3.zip, Firmware.19.0.0.zip (Switch).

**Storage.** Listed in `.gitignore` so they stay out of git history. The
`large-files` release is excluded from cleanup (the build workflow only
deletes version-tagged releases).

**Build-time restore.** The build workflow downloads all assets from
`large-files` into `.cache/large/` and copies them to their expected paths
before pack generation.

**Upload.** To add or update a large file:

```bash
gh release upload large-files "bios/Sony/PS3/PS3UPDAT.PUP#PS3UPDAT.PUP"
```

**Local cache.** `generate_pack.py` calls `fetch_large_file()` which downloads
from the release and caches in `.cache/large/` for subsequent runs.

## Manual release process

When `build.yml` is disabled, build and release manually:

```bash
# Run the full pipeline (DB + verify + packs + consistency check)
python scripts/pipeline.py --offline

# Or step by step:
python scripts/generate_db.py --force --bios-dir bios --output database.json
python scripts/verify.py --all
python scripts/generate_pack.py --all --output-dir dist/

# Create the release
DATE=$(date +%Y.%m.%d)
gh release create "v${DATE}" dist/*.zip \
  --title "BIOS Pack v${DATE}" \
  --notes "Release notes here" \
  --latest
```

To re-enable automated releases, remove the `if: false` guard from the
`release` job in `build.yml`.

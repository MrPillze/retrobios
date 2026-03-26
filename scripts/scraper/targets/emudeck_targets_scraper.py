"""Scraper for EmuDeck emulator targets.

Sources:
  SteamOS: dragoonDorise/EmuDeck — checkBIOS.sh, install scripts
  Windows: EmuDeck/emudeck-we — checkBIOS.ps1
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import yaml

from . import BaseTargetScraper

PLATFORM_NAME = "emudeck"

STEAMOS_CHECKBIOS_URL = (
    "https://raw.githubusercontent.com/dragoonDorise/EmuDeck/"
    "main/functions/checkBIOS.sh"
)
WINDOWS_CHECKBIOS_URL = (
    "https://raw.githubusercontent.com/EmuDeck/emudeck-we/"
    "main/functions/checkBIOS.ps1"
)

# Patterns for emulator name extraction from shell install/check functions
_SH_EMULATOR_RE = re.compile(
    r'(?:function\s+|^)(?:check|install|setup)([A-Za-z0-9_]+)\s*\(',
    re.MULTILINE,
)
_PS1_EMULATOR_RE = re.compile(
    r'function\s+(?:check|install|setup)([A-Za-z0-9_]+)\s*(?:\(\))?\s*\{',
    re.MULTILINE | re.IGNORECASE,
)


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "retrobios-scraper/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"  skip {url}: {e}", file=sys.stderr)
        return None


def _extract_sh_emulators(text: str) -> list[str]:
    """Extract emulator names from checkBIOS.sh function declarations."""
    seen: set[str] = set()
    results: list[str] = []
    for m in _SH_EMULATOR_RE.finditer(text):
        name = m.group(1).lower()
        if name and name not in seen:
            seen.add(name)
            results.append(name)
    return sorted(results)


def _extract_ps1_emulators(text: str) -> list[str]:
    """Extract emulator names from checkBIOS.ps1 function declarations."""
    seen: set[str] = set()
    results: list[str] = []
    for m in _PS1_EMULATOR_RE.finditer(text):
        name = m.group(1).lower()
        if name and name not in seen:
            seen.add(name)
            results.append(name)
    return sorted(results)


class Scraper(BaseTargetScraper):
    """Fetches emulator lists for EmuDeck SteamOS and Windows targets."""

    def __init__(self, url: str = "https://github.com/dragoonDorise/EmuDeck"):
        super().__init__(url=url)

    def fetch_targets(self) -> dict:
        print("  fetching SteamOS checkBIOS.sh...", file=sys.stderr)
        sh_text = _fetch(STEAMOS_CHECKBIOS_URL)
        steamos_cores = _extract_sh_emulators(sh_text) if sh_text else []

        print("  fetching Windows checkBIOS.ps1...", file=sys.stderr)
        ps1_text = _fetch(WINDOWS_CHECKBIOS_URL)
        windows_cores = _extract_ps1_emulators(ps1_text) if ps1_text else []

        targets: dict[str, dict] = {
            "steamos": {
                "architecture": "x86_64",
                "cores": steamos_cores,
            },
            "windows": {
                "architecture": "x86_64",
                "cores": windows_cores,
            },
        }

        return {
            "platform": "emudeck",
            "source": self.url,
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "targets": targets,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape EmuDeck emulator targets"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show target summary")
    parser.add_argument("--output", "-o", help="Output YAML file")
    args = parser.parse_args()

    scraper = Scraper()
    data = scraper.fetch_targets()

    if args.dry_run:
        for name, info in data["targets"].items():
            print(f"  {name} ({info['architecture']}): {len(info['cores'])} emulators")
        return

    if args.output:
        scraper.write_output(data, args.output)
        print(f"Written to {args.output}")
        return

    print(yaml.dump(data, default_flow_style=False, sort_keys=False))


if __name__ == "__main__":
    main()

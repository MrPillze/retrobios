"""Scraper for RetroPie package availability per platform.

Source: https://retropie.org.uk/stats/pkgflags/
Parses the HTML table of packages × platforms.
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

PLATFORM_NAME = "retropie"

SOURCE_URL = "https://retropie.org.uk/stats/pkgflags/"

# Maps table column header to (target_name, architecture)
_COLUMN_MAP: dict[str, tuple[str, str]] = {
    "rpi1": ("rpi1", "armv6"),
    "rpi2": ("rpi2", "armv7"),
    "rpi3": ("rpi3", "armv7"),
    "rpi4": ("rpi4", "aarch64"),
    "rpi5": ("rpi5", "aarch64"),
    "x86": ("x86", "x86"),
    "x86_64": ("x86_64", "x86_64"),
}

_TH_RE = re.compile(r'<th[^>]*>(.*?)</th>', re.IGNORECASE | re.DOTALL)
_TR_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.IGNORECASE | re.DOTALL)
_TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


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


def _parse_table(html: str) -> dict[str, list[str]]:
    """Parse the pkgflags HTML table into {target: [packages]}."""
    # Extract header row to find column indices
    header_match = re.search(
        r'<thead[^>]*>(.*?)</thead>', html, re.IGNORECASE | re.DOTALL
    )
    if not header_match:
        # Fallback: find first tr
        header_match = re.search(
            r'<tr[^>]*>(.*?)</tr>', html, re.IGNORECASE | re.DOTALL
        )
    if not header_match:
        return {}

    headers = [_strip_tags(h).lower() for h in _TH_RE.findall(header_match.group(1))]
    # Find which column index maps to which target
    col_targets: dict[int, tuple[str, str]] = {}
    for i, h in enumerate(headers):
        if h in _COLUMN_MAP:
            col_targets[i] = _COLUMN_MAP[h]

    if not col_targets:
        return {}

    # Initialize result
    result: dict[str, list[str]] = {name: [] for name, _ in col_targets.values()}

    # Parse body rows
    tbody_match = re.search(
        r'<tbody[^>]*>(.*?)</tbody>', html, re.IGNORECASE | re.DOTALL
    )
    body_html = tbody_match.group(1) if tbody_match else html

    for tr_match in _TR_RE.finditer(body_html):
        cells = [_strip_tags(td) for td in _TD_RE.findall(tr_match.group(1))]
        if not cells:
            continue
        # First cell is package name
        package = cells[0].strip().lower()
        if not package:
            continue
        for col_idx, (target_name, _arch) in col_targets.items():
            if col_idx < len(cells):
                cell_val = cells[col_idx].strip().lower()
                # Any non-empty, non-dash, non-zero value = available
                if cell_val and cell_val not in ("", "-", "0", "n", "no", "false"):
                    result[target_name].append(package)

    return result


class Scraper(BaseTargetScraper):
    """Fetches RetroPie package availability per platform from pkgflags page."""

    def __init__(self, url: str = SOURCE_URL):
        super().__init__(url=url)

    def fetch_targets(self) -> dict:
        print("  fetching RetroPie pkgflags...", file=sys.stderr)
        html = _fetch(self.url)
        packages_per_target: dict[str, list[str]] = {}
        if html:
            packages_per_target = _parse_table(html)

        targets: dict[str, dict] = {}
        for col_key, (target_name, arch) in _COLUMN_MAP.items():
            targets[target_name] = {
                "architecture": arch,
                "cores": sorted(packages_per_target.get(target_name, [])),
            }

        return {
            "platform": "retropie",
            "source": self.url,
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "targets": targets,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape RetroPie package targets"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show target summary")
    parser.add_argument("--output", "-o", help="Output YAML file")
    args = parser.parse_args()

    scraper = Scraper()
    data = scraper.fetch_targets()

    if args.dry_run:
        for name, info in data["targets"].items():
            print(f"  {name} ({info['architecture']}): {len(info['cores'])} packages")
        return

    if args.output:
        scraper.write_output(data, args.output)
        print(f"Written to {args.output}")
        return

    print(yaml.dump(data, default_flow_style=False, sort_keys=False))


if __name__ == "__main__":
    main()

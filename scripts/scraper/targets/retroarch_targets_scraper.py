"""Scraper for RetroArch buildbot nightly targets.

Source: https://buildbot.libretro.com/nightly/
Fetches directory listings per target to determine available cores.
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

PLATFORM_NAME = "retroarch"

BUILDBOT_URL = "https://buildbot.libretro.com/nightly/"

# (path, target_name, architecture)
TARGETS: list[tuple[str, str, str]] = [
    ("linux/x86_64", "linux-x86_64", "x86_64"),
    ("linux/armhf", "linux-armhf", "armhf"),
    ("linux/armv7-neon-hf", "linux-armv7-neon-hf", "armv7"),
    ("windows/x86_64", "windows-x86_64", "x86_64"),
    ("windows/x86", "windows-x86", "x86"),
    ("android/armeabi-v7a", "android-armeabi-v7a", "armv7"),
    ("android/arm64-v8a", "android-arm64-v8a", "aarch64"),
    ("apple/osx/x86_64", "osx-x86_64", "x86_64"),
    ("apple/osx/arm64", "osx-arm64", "aarch64"),
    ("apple/ios-arm64", "ios-arm64", "aarch64"),
    ("apple/tvos-arm64", "tvos-arm64", "aarch64"),
    ("nintendo/switch/libnx", "switch-libnx", "aarch64"),
    ("nintendo/3ds", "3ds", "armv6"),
    ("nintendo/ngc", "ngc", "ppc"),
    ("nintendo/wii", "wii", "ppc"),
    ("nintendo/wiiu", "wiiu", "ppc"),
    ("playstation/ps2", "ps2", "mips"),
    ("playstation/psp", "psp", "mips"),
    ("playstation/vita", "vita", "armv7"),
]

_CORE_RE = re.compile(
    r'href="([^"]+_libretro(?:\.so|\.dll|\.dylib)(?:\.zip)?)"',
    re.IGNORECASE,
)


def _strip_core_suffix(filename: str) -> str:
    """Strip _libretro.so/.dll/.dylib(.zip)? suffix to get core name."""
    name = re.sub(r'\.zip$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'_libretro(?:\.so|\.dll|\.dylib)$', '', name, flags=re.IGNORECASE)
    return name


class Scraper(BaseTargetScraper):
    """Fetches core lists per target from RetroArch buildbot nightly."""

    def __init__(self, url: str = BUILDBOT_URL):
        super().__init__(url=url)

    def _fetch_url(self, url: str) -> str | None:
        """Fetch URL, return text or None on failure."""
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "retrobios-scraper/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            print(f"  skip {url}: {e}", file=sys.stderr)
            return None

    def _fetch_cores_for_target(self, path: str) -> list[str]:
        """Fetch core list from buildbot directory listing."""
        url = f"{self.url}{path}/latest/"
        html = self._fetch_url(url)
        if html is None:
            return []
        cores = []
        seen: set[str] = set()
        for match in _CORE_RE.finditer(html):
            filename = match.group(1).split("/")[-1]
            core = _strip_core_suffix(filename)
            if core and core not in seen:
                seen.add(core)
                cores.append(core)
        return sorted(cores)

    def fetch_targets(self) -> dict:
        """Fetch all targets and their core lists."""
        targets: dict[str, dict] = {}
        for path, target_name, arch in TARGETS:
            print(f"  fetching {target_name}...", file=sys.stderr)
            cores = self._fetch_cores_for_target(path)
            if not cores:
                print(f"  warning: no cores found for {target_name}", file=sys.stderr)
            targets[target_name] = {
                "architecture": arch,
                "cores": cores,
            }
        return {
            "platform": "retroarch",
            "source": self.url,
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "targets": targets,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape RetroArch buildbot nightly targets"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show target summary")
    parser.add_argument("--output", "-o", help="Output YAML file")
    args = parser.parse_args()

    scraper = Scraper()
    data = scraper.fetch_targets()

    if args.dry_run:
        for name, info in data["targets"].items():
            print(f"  {name} ({info['architecture']}): {len(info['cores'])} cores")
        return

    if args.output:
        scraper.write_output(data, args.output)
        print(f"Written to {args.output}")
        return

    print(yaml.dump(data, default_flow_style=False, sort_keys=False))


if __name__ == "__main__":
    main()

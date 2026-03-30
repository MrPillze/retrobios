"""Exporter for RomM known_bios_files.json format.

Produces JSON matching the exact format of
rommapp/romm/backend/models/fixtures/known_bios_files.json:
- Keys are "igdb_slug:filename"
- Values contain size, crc, md5, sha1 (all optional but at least one hash)
- Hashes are lowercase hex strings
- Size is an integer
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from .base_exporter import BaseExporter

# retrobios slug -> IGDB slug (reverse of scraper SLUG_MAP)
_REVERSE_SLUG: dict[str, str] = {
    "3do": "3do",
    "nintendo-64dd": "64dd",
    "amstrad-cpc": "acpc",
    "commodore-amiga": "amiga",
    "arcade": "arcade",
    "atari-st": "atari-st",
    "atari-5200": "atari5200",
    "atari-7800": "atari7800",
    "atari-400-800": "atari8bit",
    "coleco-colecovision": "colecovision",
    "sega-dreamcast": "dc",
    "doom": "doom",
    "enterprise-64-128": "enterprise",
    "fairchild-channel-f": "fairchild-channel-f",
    "nintendo-fds": "fds",
    "sega-game-gear": "gamegear",
    "nintendo-gb": "gb",
    "nintendo-gba": "gba",
    "nintendo-gbc": "gbc",
    "sega-mega-drive": "genesis",
    "mattel-intellivision": "intellivision",
    "j2me": "j2me",
    "atari-lynx": "lynx",
    "apple-macintosh-ii": "mac",
    "microsoft-msx": "msx",
    "nintendo-ds": "nds",
    "snk-neogeo-cd": "neo-geo-cd",
    "nintendo-nes": "nes",
    "nintendo-gamecube": "ngc",
    "magnavox-odyssey2": "odyssey-2-slash-videopac-g7000",
    "nec-pc-98": "pc-9800-series",
    "nec-pc-fx": "pc-fx",
    "nintendo-pokemon-mini": "pokemon-mini",
    "sony-playstation-2": "ps2",
    "sony-psp": "psp",
    "sony-playstation": "psx",
    "nintendo-satellaview": "satellaview",
    "sega-saturn": "saturn",
    "scummvm": "scummvm",
    "sega-mega-cd": "segacd",
    "sharp-x68000": "sharp-x68000",
    "sega-master-system": "sms",
    "nintendo-snes": "snes",
    "nintendo-sufami-turbo": "sufami-turbo",
    "nintendo-sgb": "super-gb",
    "nec-pc-engine": "tg16",
    "videoton-tvc": "tvc",
    "philips-videopac": "videopac-g7400",
    "wolfenstein-3d": "wolfenstein",
    "sharp-x1": "x1",
    "microsoft-xbox": "xbox",
    "sinclair-zx-spectrum": "zxs",
}


class Exporter(BaseExporter):
    """Export truth data to RomM known_bios_files.json format."""

    @staticmethod
    def platform_name() -> str:
        return "romm"

    def export(
        self,
        truth_data: dict,
        output_path: str,
        scraped_data: dict | None = None,
    ) -> None:
        native_map: dict[str, str] = {}
        if scraped_data:
            for sys_id, sys_data in scraped_data.get("systems", {}).items():
                nid = sys_data.get("native_id")
                if nid:
                    native_map[sys_id] = nid

        output: OrderedDict[str, dict] = OrderedDict()

        systems = truth_data.get("systems", {})
        for sys_id in sorted(systems):
            sys_data = systems[sys_id]
            files = sys_data.get("files", [])
            if not files:
                continue

            igdb_slug = native_map.get(sys_id, _REVERSE_SLUG.get(sys_id, sys_id))

            for fe in files:
                name = fe.get("name", "")
                if name.startswith("_") or self._is_pattern(name):
                    continue

                key = f"{igdb_slug}:{name}"

                entry: OrderedDict[str, object] = OrderedDict()

                size = fe.get("size")
                if size is not None:
                    entry["size"] = int(size)

                crc = fe.get("crc32", "")
                if crc:
                    entry["crc"] = str(crc).strip().lower()

                md5 = fe.get("md5", "")
                if isinstance(md5, list):
                    md5 = md5[0] if md5 else ""
                if md5:
                    entry["md5"] = str(md5).strip().lower()

                sha1 = fe.get("sha1", "")
                if isinstance(sha1, list):
                    sha1 = sha1[0] if sha1 else ""
                if sha1:
                    entry["sha1"] = str(sha1).strip().lower()

                output[key] = entry

        Path(output_path).write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def validate(self, truth_data: dict, output_path: str) -> list[str]:
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))

        exported_names: set[str] = set()
        for key in data:
            if ":" in key:
                _, filename = key.split(":", 1)
                exported_names.add(filename)

        issues: list[str] = []
        for sys_data in truth_data.get("systems", {}).values():
            for fe in sys_data.get("files", []):
                name = fe.get("name", "")
                if name.startswith("_") or self._is_pattern(name):
                    continue
                if name not in exported_names:
                    issues.append(f"missing: {name}")
        return issues

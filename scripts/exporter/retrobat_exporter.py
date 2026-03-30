"""Exporter for RetroBat batocera-systems.json format.

Produces JSON matching the exact format of
RetroBat-Official/emulatorlauncher/batocera-systems/Resources/batocera-systems.json:
- System keys with "name" and "biosFiles" fields
- Each biosFile has "md5" before "file" (matching original key order)
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from .base_exporter import BaseExporter


def _slug_to_display(slug: str) -> str:
    """Convert slug to display name."""
    return slug.replace("-", " ").title()


class Exporter(BaseExporter):
    """Export truth data to RetroBat batocera-systems.json format."""

    @staticmethod
    def platform_name() -> str:
        return "retrobat"

    def export(
        self,
        truth_data: dict,
        output_path: str,
        scraped_data: dict | None = None,
    ) -> None:
        native_map: dict[str, str] = {}
        display_map: dict[str, str] = {}
        if scraped_data:
            for sys_id, sys_data in scraped_data.get("systems", {}).items():
                nid = sys_data.get("native_id")
                if nid:
                    native_map[sys_id] = nid
                dname = sys_data.get("name")
                if dname:
                    display_map[sys_id] = dname

        output: OrderedDict[str, dict] = OrderedDict()

        systems = truth_data.get("systems", {})
        for sys_id in sorted(systems):
            sys_data = systems[sys_id]
            files = sys_data.get("files", [])
            if not files:
                continue

            native_id = native_map.get(sys_id, sys_id)
            display_name = display_map.get(sys_id, _slug_to_display(sys_id))
            bios_files: list[OrderedDict] = []

            for fe in files:
                name = fe.get("name", "")
                if name.startswith("_") or self._is_pattern(name):
                    continue
                dest = fe.get("destination", name)
                md5 = fe.get("md5", "")
                if isinstance(md5, list):
                    md5 = md5[0] if md5 else ""

                # Original format has md5 before file
                entry: OrderedDict[str, str] = OrderedDict()
                if md5:
                    entry["md5"] = md5
                entry["file"] = f"bios/{dest}"
                bios_files.append(entry)

            if bios_files:
                sys_entry: OrderedDict[str, object] = OrderedDict()
                sys_entry["name"] = display_name
                sys_entry["biosFiles"] = bios_files
                output[native_id] = sys_entry

        Path(output_path).write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def validate(self, truth_data: dict, output_path: str) -> list[str]:
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))

        exported_files: set[str] = set()
        for sys_data in data.values():
            for bf in sys_data.get("biosFiles", []):
                path = bf.get("file", "")
                stripped = path.removeprefix("bios/")
                exported_files.add(stripped)
                basename = path.split("/")[-1] if "/" in path else path
                exported_files.add(basename)

        issues: list[str] = []
        for sys_data in truth_data.get("systems", {}).values():
            for fe in sys_data.get("files", []):
                name = fe.get("name", "")
                if name.startswith("_") or self._is_pattern(name):
                    continue
                dest = fe.get("destination", name)
                if name not in exported_files and dest not in exported_files:
                    issues.append(f"missing: {name}")
        return issues

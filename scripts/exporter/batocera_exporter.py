"""Exporter for Batocera batocera-systems format (Python dict)."""

from __future__ import annotations

from pathlib import Path

from .base_exporter import BaseExporter


class Exporter(BaseExporter):
    """Export truth data to Batocera batocera-systems format."""

    @staticmethod
    def platform_name() -> str:
        return "batocera"

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

        lines: list[str] = [
            "#!/usr/bin/env python3",
            "# Generated batocera-systems BIOS declarations",
            "from collections import OrderedDict",
            "",
            "systems = {",
        ]

        systems = truth_data.get("systems", {})
        for sys_id in sorted(systems):
            sys_data = systems[sys_id]
            files = sys_data.get("files", [])
            if not files:
                continue

            native_id = native_map.get(sys_id, sys_id)
            lines.append(f'    "{native_id}": {{')
            lines.append('        "biosFiles": [')

            for fe in files:
                name = fe.get("name", "")
                if name.startswith("_"):
                    continue
                dest = fe.get("destination", name)
                md5 = fe.get("md5", "")
                if isinstance(md5, list):
                    md5 = md5[0] if md5 else ""

                lines.append("            {")
                lines.append(f'                "file": "bios/{dest}",')
                lines.append(f'                "md5": "{md5}",')
                lines.append("            },")

            lines.append("        ],")
            lines.append("    },")

        lines.append("}")
        lines.append("")
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    def validate(self, truth_data: dict, output_path: str) -> list[str]:
        content = Path(output_path).read_text(encoding="utf-8")
        issues: list[str] = []
        for sys_data in truth_data.get("systems", {}).values():
            for fe in sys_data.get("files", []):
                name = fe.get("name", "")
                if name.startswith("_"):
                    continue
                if name not in content:
                    issues.append(f"missing: {name}")
        return issues

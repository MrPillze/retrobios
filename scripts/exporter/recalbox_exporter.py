"""Exporter for Recalbox es_bios.xml format."""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from .base_exporter import BaseExporter


class Exporter(BaseExporter):
    """Export truth data to Recalbox es_bios.xml format."""

    @staticmethod
    def platform_name() -> str:
        return "recalbox"

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

        root = Element("biosList")

        systems = truth_data.get("systems", {})
        for sys_id in sorted(systems):
            sys_data = systems[sys_id]
            files = sys_data.get("files", [])
            if not files:
                continue

            native_id = native_map.get(sys_id, sys_id)
            system_el = SubElement(root, "system", platform=native_id)

            for fe in files:
                name = fe.get("name", "")
                if name.startswith("_"):
                    continue

                dest = fe.get("destination", name)
                md5 = fe.get("md5", "")
                if isinstance(md5, list):
                    md5 = ",".join(md5)
                required = fe.get("required", False)

                attrs = {
                    "path": dest,
                    "md5": md5,
                    "mandatory": "true" if required else "false",
                    "hashMatchMandatory": "true" if required else "false",
                }
                SubElement(system_el, "bios", **attrs)

        indent(root, space="    ")
        tree = ElementTree(root)
        tree.write(output_path, encoding="unicode", xml_declaration=True)
        # Add trailing newline
        with open(output_path, "a") as f:
            f.write("\n")

    def validate(self, truth_data: dict, output_path: str) -> list[str]:
        from xml.etree.ElementTree import parse as xml_parse

        tree = xml_parse(output_path)
        root = tree.getroot()

        exported_paths: set[str] = set()
        for bios_el in root.iter("bios"):
            path = bios_el.get("path", "")
            if path:
                exported_paths.add(path)

        issues: list[str] = []
        for sys_data in truth_data.get("systems", {}).values():
            for fe in sys_data.get("files", []):
                name = fe.get("name", "")
                if name.startswith("_"):
                    continue
                dest = fe.get("destination", name)
                if dest not in exported_paths:
                    issues.append(f"missing: {dest}")
        return issues

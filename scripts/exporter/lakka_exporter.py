"""Exporter for Lakka (System.dat format, same as RetroArch).

Lakka inherits RetroArch cores and uses the same System.dat format.
Delegates to systemdat_exporter for export and validation.
"""

from __future__ import annotations

from .systemdat_exporter import Exporter as SystemDatExporter


class Exporter(SystemDatExporter):
    """Export truth data to Lakka System.dat format."""

    @staticmethod
    def platform_name() -> str:
        return "lakka"

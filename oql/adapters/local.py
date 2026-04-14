"""Local adapter — directly invokes oqlos CQL interpreter."""

from __future__ import annotations

from typing import Any


class LocalAdapter:
    """Execute OQL commands directly via oqlos library."""

    def __init__(self, firmware_url: str = "http://localhost:8202"):
        self._firmware_url = firmware_url

    def execute(self, command: str) -> Any:
        """Execute a single OQL command line."""
        from oqlos.core.interpreter import CqlInterpreter

        interp = CqlInterpreter(mode="dry-run", firmware_url=self._firmware_url, quiet=False)
        result = interp.run(command, "<shell>")
        return result

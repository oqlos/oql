"""Remote adapter — calls oqlos via HTTP API."""

from __future__ import annotations

from typing import Any

import httpx


class RemoteAdapter:
    """Execute OQL commands via OqlOS REST API."""

    def __init__(self, base_url: str = "http://localhost:8200"):
        self._base_url = base_url.rstrip("/")

    def execute(self, command: str) -> Any:
        """Send a command to the oqlos API."""
        resp = httpx.post(
            f"{self._base_url}/api/execute",
            json={"command": command},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def list_scenarios(self) -> list[dict]:
        resp = httpx.get(f"{self._base_url}/api/scenarios", timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def list_hardware(self) -> list[dict]:
        resp = httpx.get(f"{self._base_url}/api/hardware/peripherals", timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])

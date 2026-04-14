"""UI command handlers: NAVIGATE, CLICK, INPUT."""

from __future__ import annotations

from typing import Any, Dict


class UiCommandsMixin:
    """Commands for browser UI interaction."""

    async def cmd_navigate(self, args: str) -> Dict:
        """NAVIGATE "/route" """
        route = args.strip().strip('"\'')
        event = await self.emit_event("navigation.navigated", {"route": route})
        print(f"📍 NAVIGATE {route}")
        return event

    async def cmd_click(self, args: str) -> Dict:
        """CLICK "#selector" {"label": "..."} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("ui.button_clicked", {
            "selector": parts[0],
            **parts[1]
        })
        print(f"🖱️ CLICK {parts[0]}")
        return event

    async def cmd_input(self, args: str) -> Dict:
        """INPUT "#selector" {"value": "..."} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("ui.input_changed", {
            "selector": parts[0],
            **parts[1]
        })
        print(f"⌨️ INPUT {parts[0]} = {parts[1].get('value', '')}")
        return event

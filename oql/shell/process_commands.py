"""Process and component command handlers."""

from __future__ import annotations

import json
from typing import Any, Dict


class ProcessCommandsMixin:
    """Commands for process flow, components, state, and events."""

    async def cmd_emit(self, args: str) -> Dict:
        """EMIT "event.type" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event(parts[0], parts[1])
        print(f"📣 EMIT {parts[0]}")
        return event

    async def cmd_render(self, args: str) -> Dict:
        """RENDER "component-name" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("component.render_requested", {
            "componentName": parts[0],
            "props": parts[1]
        })
        print(f"🎨 RENDER {parts[0]}")
        return event

    async def cmd_layout(self, args: str) -> Dict:
        """LAYOUT "layout-name" """
        layout = args.strip().strip('"\'')
        event = await self.emit_event("layout.changed", {"layout": layout})
        print(f"📐 LAYOUT {layout}")
        return event

    async def cmd_state_save(self, args: str) -> Dict:
        """STATE_SAVE "name" """
        name = args.strip().strip('"\'')
        event = await self.emit_event("state.saved", {"name": name})
        print(f"💾 STATE_SAVE {name}")
        return event

    async def cmd_state_restore(self, args: str) -> Dict:
        """STATE_RESTORE "name" """
        name = args.strip().strip('"\'')
        event = await self.emit_event("state.restored", {"name": name})
        print(f"📂 STATE_RESTORE {name}")
        return event

    async def cmd_process_start(self, args: str) -> Dict:
        """PROCESS_START "process-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("process.started", {
            "processId": parts[0],
            "context": parts[1]
        })
        print(f"▶️ PROCESS_START {parts[0]}")
        return event

    async def cmd_process_next(self, args: str) -> Dict:
        """PROCESS_NEXT {...} """
        try:
            data = json.loads(args) if args.strip() else {}
        except Exception:
            data = {}
        event = await self.emit_event("process.step_completed", {"data": data})
        print(f"➡️ PROCESS_NEXT")
        return event

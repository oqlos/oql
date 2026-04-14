"""Protocol / test-flow command handlers."""

from __future__ import annotations

from typing import Any, Dict


class ProtocolCommandsMixin:
    """Commands for test flow and protocol management."""

    async def cmd_select_device(self, args: str) -> Dict:
        """SELECT_DEVICE "device-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("test.device_selected", {
            "deviceId": parts[0],
            **parts[1]
        })
        print(f"📱 SELECT_DEVICE {parts[0]}")
        return event

    async def cmd_select_interval(self, args: str) -> Dict:
        """SELECT_INTERVAL "code" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("test.interval_selected", {
            "intervalCode": parts[0],
            **parts[1]
        })
        print(f"⏱️ SELECT_INTERVAL {parts[0]}")
        return event

    async def cmd_start_test(self, args: str) -> Dict:
        """START_TEST "scenario-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("test.started", {
            "scenarioId": parts[0],
            **parts[1]
        })
        print(f"🧪 START_TEST {parts[0]}")
        return event

    async def cmd_step_complete(self, args: str) -> Dict:
        """STEP_COMPLETE "step-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("test.step_executed", {
            "stepId": parts[0],
            **parts[1]
        })
        status = parts[1].get('status', 'completed')
        icon = "✅" if status == "passed" else "❌" if status == "failed" else "⏭️"
        print(f"{icon} STEP_COMPLETE {parts[0]} [{status}]")
        return event

    async def cmd_protocol_created(self, args: str) -> Dict:
        """PROTOCOL_CREATED "protocol-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("protocol.created", {
            "protocolId": parts[0],
            **parts[1]
        })
        print(f"📋 PROTOCOL_CREATED {parts[0]}")
        return event

    async def cmd_protocol_finalize(self, args: str) -> Dict:
        """PROTOCOL_FINALIZE "protocol-id" {...} """
        parts = self._parse_target_and_json(args)
        event = await self.emit_event("protocol.finalized", {
            "protocolId": parts[0],
            **parts[1]
        })
        print(f"✔️ PROTOCOL_FINALIZE {parts[0]}")
        return event

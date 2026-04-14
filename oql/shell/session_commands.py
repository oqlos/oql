"""Session / utility command handlers."""

from __future__ import annotations

import asyncio
from typing import Any, Dict


class SessionCommandsMixin:
    """Commands for recording sessions, waiting, logging, and help."""

    async def cmd_record_start(self, args: str) -> Dict:
        """RECORD_START ["user-id"] """
        user_id = args.strip().strip('"\'') if args.strip() else None
        self.recording = True
        self.session_events = []
        self.correlation_id = self._generate_id()
        event = await self.emit_event("session.started", {
            "sessionId": self.correlation_id,
            "userId": user_id
        })
        print(f"🔴 RECORD_START session={self.correlation_id}")
        return event

    async def cmd_record_stop(self, args: str) -> Dict:
        """RECORD_STOP """
        self.recording = False
        event = await self.emit_event("session.ended", {
            "sessionId": self.correlation_id,
            "eventsCount": len(self.session_events)
        })
        print(f"⏹️ RECORD_STOP ({len(self.session_events)} events)")
        return event

    async def cmd_wait(self, args: str) -> None:
        """WAIT <ms> """
        ms = int(args.strip())
        await asyncio.sleep(ms / 1000)
        print(f"⏳ WAIT {ms}ms")

    async def cmd_log(self, args: str) -> None:
        """LOG "message" {...} """
        parts = self._parse_target_and_json(args)
        level = parts[1].get('level', 'info')
        icons = {'info': 'ℹ️', 'warn': '⚠️', 'error': '❌', 'debug': '🔍'}
        print(f"{icons.get(level, 'ℹ️')} {parts[0]}")

    async def cmd_help(self, args: str) -> None:
        """Show help"""
        print("""
📋 DSL Shell Commands:

Navigation:
  NAVIGATE "/route"                    - Navigate to route

UI Actions:
  CLICK "#selector" {...}              - Click element
  INPUT "#selector" {"value": "..."}   - Set input value

Test Flow:
  SELECT_DEVICE "id" {...}             - Select device
  SELECT_INTERVAL "code" {...}         - Select interval
  START_TEST "scenario" {...}          - Start test
  STEP_COMPLETE "step" {...}           - Complete step
  PROTOCOL_CREATED "id" {...}          - Protocol created
  PROTOCOL_FINALIZE "id" {...}         - Finalize protocol

Components:
  LAYOUT "layout-name"                 - Set layout
  RENDER "component" {...}             - Render component

State:
  STATE_SAVE "name"                    - Save state
  STATE_RESTORE "name"                 - Restore state

Process:
  PROCESS_START "process-id" {...}     - Start process
  PROCESS_NEXT {...}                   - Next step

Session:
  RECORD_START ["user-id"]             - Start recording
  RECORD_STOP                          - Stop recording

Events:
  EMIT "event.type" {...}              - Emit event

Other:
  WAIT <ms>                            - Wait milliseconds
  LOG "message" {"level": "info"}      - Log message
  HELP                                 - Show this help

Scripts:
  .run path/to/script.dsl              - Run DSL script
  .scripts                             - List available scripts

Special:
  .events                              - Show event store
  .clear                               - Clear event store
  .connect [url]                       - Connect to browser
  .disconnect                          - Disconnect from browser
  .exit / .quit                        - Exit shell
        """)

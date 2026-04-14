"""DSL Executor — execute DSL commands with event sourcing and WebSocket sync."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment]

from oql.core.event_store import DslEventStore as EventStore

from .api_commands import ApiCommandsMixin
from .process_commands import ProcessCommandsMixin
from .protocol_commands import ProtocolCommandsMixin
from .session_commands import SessionCommandsMixin
from .ui_commands import UiCommandsMixin


class DslExecutor(
    ApiCommandsMixin,
    UiCommandsMixin,
    ProtocolCommandsMixin,
    ProcessCommandsMixin,
    SessionCommandsMixin,
):
    """Execute DSL commands"""
    
    def __init__(self, api_url: str = "http://localhost:8101"):
        self.api_url = api_url
        self.event_store = EventStore()
        self.variables: dict[str, Any] = {}
        self.correlation_id = self._generate_id()
        self.websocket: "websockets.WebSocketClientProtocol | None" = None
        self.recording = False
        self.session_events: list[Dict] = []
        
    async def connect_websocket(self, url: str = "ws://localhost:8104/events"):
        """Connect to browser via WebSocket"""
        try:
            self.websocket = await websockets.connect(url)
            print(f"🔌 Connected to browser: {url}")
            return True
        except Exception as e:
            print(f"⚠️  WebSocket not available: {e}")
            return False
            
    async def disconnect_websocket(self):
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
            self.websocket = None
            print("🔌 Disconnected from browser")
            
    async def emit_event(self, event_type: str, payload: Dict) -> Dict:
        """Emit event (store + broadcast)"""
        event = {
            "id": self._generate_id(),
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "correlationId": self.correlation_id,
            "payload": payload,
            "metadata": {
                "source": "cli"
            }
        }
        
        self.event_store.append(event)
        
        if self.recording:
            self.session_events.append(event)
        
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(event))
            except Exception:
                pass
                
        return event

    COMMAND_REGISTRY: Dict[str, str] = {
        'navigate': 'cmd_navigate',
        'click': 'cmd_click',
        'input': 'cmd_input',
        'select_device': 'cmd_select_device',
        'select_interval': 'cmd_select_interval',
        'start_test': 'cmd_start_test',
        'step_complete': 'cmd_step_complete',
        'protocol_created': 'cmd_protocol_created',
        'protocol_finalize': 'cmd_protocol_finalize',
        'layout': 'cmd_layout',
        'render': 'cmd_render',
        'state_save': 'cmd_state_save',
        'state_restore': 'cmd_state_restore',
        'emit': 'cmd_emit',
        'api': 'cmd_api',
        'create_protocol': 'cmd_create_protocol',
        'process_start': 'cmd_process_start',
        'process_next': 'cmd_process_next',
        'record_start': 'cmd_record_start',
        'record_stop': 'cmd_record_stop',
        'wait': 'cmd_wait',
        'log': 'cmd_log',
        'help': 'cmd_help',
    }

    async def execute(self, command: str) -> Any:
        """Execute a single DSL command via registry dispatch."""
        command = command.strip()
        if not command or command.startswith('#'):
            return None

        parts = command.split(None, 1)
        action = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""

        handler_name = self.COMMAND_REGISTRY.get(action.lower())
        if handler_name:
            handler = getattr(self, handler_name)
            return await handler(args)

        print(f"❓ Unknown command: {action}")
        return None

    async def execute_script(self, script: str) -> None:
        """Execute multiple commands"""
        lines = script.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                await self.execute(line)

    # ========================================================================
    # Helpers
    # ========================================================================
    
    def _parse_target_and_json(self, args: str) -> tuple:
        """Parse 'target' {...} format"""
        args = args.strip()
        
        target = ""
        rest = args
        
        if args.startswith('"'):
            end = args.find('"', 1)
            if end > 0:
                target = args[1:end]
                rest = args[end + 1:].strip()
        elif args.startswith("'"):
            end = args.find("'", 1)
            if end > 0:
                target = args[1:end]
                rest = args[end + 1:].strip()
        else:
            parts = args.split(None, 1)
            target = parts[0] if parts else ""
            rest = parts[1] if len(parts) > 1 else ""
            
        data = {}
        if rest.startswith('{'):
            try:
                data = json.loads(rest)
            except Exception:
                pass
                
        return (target, data)
        
    def _generate_id(self) -> str:
        import time
        import random
        return f"evt-{int(time.time() * 1000):x}-{random.randint(0, 0xffff):04x}"

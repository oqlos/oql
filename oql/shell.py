#!/usr/bin/env python3
"""
DSL Shell - Interactive CLI for DSL execution with browser sync

Usage:
  python dsl-shell.py                    # Interactive mode
  python dsl-shell.py script.dsl         # Execute script
  python dsl-shell.py -c "NAVIGATE /x"   # Execute command
  
Features:
  - Execute DSL commands
  - WebSocket sync with browser
  - Session recording/replay
  - Event sourcing integration
"""

import asyncio
import json
import sys
import os
import readline
import websockets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# No sys.path hack needed — proper package

# ============================================================================
# Event Store — canonical: dsl/core/event_store.py
# ============================================================================

from oql.core.event_store import DslEventStore as EventStore

# ============================================================================
# DSL Executor
# ============================================================================

class DslExecutor:
    """Execute DSL commands"""
    
    def __init__(self, api_url: str = "http://localhost:8101"):
        self.api_url = api_url
        self.event_store = EventStore()
        self.variables: dict[str, Any] = {}
        self.correlation_id = self._generate_id()
        self.websocket: websockets.WebSocketClientProtocol | None = None
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
                pass  # Ignore close errors
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
        
        # Send to browser if connected
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(event))
            except Exception:
                pass
                
        return event
        
    async def execute(self, command: str) -> Any:
        """Execute a single DSL command"""
        command = command.strip()
        if not command or command.startswith('#'):
            return None
            
        parts = command.split(None, 1)
        action = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        
        # Route to handler
        handler = getattr(self, f'cmd_{action.lower()}', None)
        if handler:
            return await handler(args)
        else:
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
    # Command Handlers
    # ========================================================================
    
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

    async def cmd_api(self, args: str) -> Dict:
        """API GET|POST|PUT|DELETE "url" {...} """
        import urllib.request
        import urllib.error
        
        parts = args.strip().split(None, 2)
        if len(parts) < 2:
            print("❌ Usage: API GET|POST|PUT|DELETE \"url\" {...}")
            return {}
        
        method = parts[0].upper()
        url = parts[1].strip('"\'')
        data = {}
        if len(parts) > 2 and parts[2].startswith('{'):
            try:
                data = json.loads(parts[2])
            except Exception:
                pass
        
        # Add base URL if relative
        if url.startswith('/'):
            url = f"{self.api_url}{url}"
        
        try:
            req_data = json.dumps(data).encode('utf-8') if data else None
            req = urllib.request.Request(
                url, 
                data=req_data,
                method=method,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                result_text = resp.read().decode('utf-8')
                try:
                    result = json.loads(result_text)
                except Exception:
                    result = {"text": result_text[:200]}
                
                icon = "✅" if status < 400 else "❌"
                print(f"{icon} API {method} {url} → {status}")
                
                # Emit event
                event = await self.emit_event("api.response", {
                    "method": method,
                    "url": url,
                    "status": status,
                    "data": result
                })
                return event
        except urllib.error.HTTPError as e:
            print(f"❌ API {method} {url} → {e.code}")
            return {}
        except Exception as e:
            print(f"❌ API Error: {e}")
            return {}

    async def cmd_create_protocol(self, args: str) -> Dict:
        """CREATE_PROTOCOL "name" {...} - Create protocol via API"""
        import urllib.request
        import urllib.error
        
        parts = self._parse_target_and_json(args)
        name = parts[0]
        data = parts[1]
        
        payload = {
            "name": name,
            "device_id": data.get("device_id", "d-test-001"),
            "status": data.get("status", "COMPLETED"),
            "test_date": data.get("test_date", datetime.now(timezone.utc).isoformat()),
            "results": data.get("results", {"passed": True}),
            **{k: v for k, v in data.items() if k not in ["device_id", "status", "test_date", "results"]}
        }
        
        try:
            req = urllib.request.Request(
                f"{self.api_url}/api/v3/data/protocols",
                data=json.dumps(payload).encode('utf-8'),
                method='POST',
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                result_text = resp.read().decode('utf-8')
                try:
                    result = json.loads(result_text)
                except Exception:
                    result = {}
                
                if status < 400:
                    protocol_id = result.get('id') or result.get('data', {}).get('id', 'unknown')
                    print(f"✅ CREATE_PROTOCOL {name} → {protocol_id}")
                    event = await self.emit_event("protocol.created", {
                        "protocolId": protocol_id,
                        "name": name,
                        **payload
                    })
                    return event
                else:
                    print(f"❌ CREATE_PROTOCOL failed: {status}")
                    return {}
        except urllib.error.HTTPError as e:
            print(f"❌ CREATE_PROTOCOL failed: {e.code}")
            return {}
        except Exception as e:
            print(f"❌ CREATE_PROTOCOL Error: {e}")
            return {}
        
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
        
    # ========================================================================
    # Helpers
    # ========================================================================
    
    def _parse_target_and_json(self, args: str) -> tuple:
        """Parse 'target' {...} format"""
        args = args.strip()
        
        # Find target (quoted string)
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
            
        # Parse JSON
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

# ============================================================================
# Interactive Shell
# ============================================================================

from typing import Dict, Any, List, Callable, Awaitable

# Shell command handler type: takes executor and line, returns True to exit shell
ShellHandler = Callable[['DslExecutor', str], Awaitable[bool]]


class ShellCommandRegistry:
    """Registry for interactive shell commands."""
    
    def __init__(self):
        self.handlers: Dict[str, ShellHandler] = {}
        self.aliases: Dict[str, str] = {}
    
    def register(self, name: str, handler: ShellHandler, aliases: List[str] = None):
        """Register a command handler with optional aliases."""
        self.handlers[name] = handler
        if aliases:
            for alias in aliases:
                self.aliases[alias] = name
    
    def get_handler(self, line: str) -> tuple[ShellHandler | None, str]:
        """Get handler for a command line. Returns (handler, args) or (None, line)."""
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        
        # Resolve alias
        canonical = self.aliases.get(cmd, cmd)
        handler = self.handlers.get(canonical)
        return handler, rest


# Global registry
SHELL_COMMANDS = ShellCommandRegistry()


# ── Command handlers ───────────────────────────────────────────────

async def _cmd_exit(ex: 'DslExecutor', args: str) -> bool:
    """Exit the shell."""
    await ex.disconnect_websocket()
    print("👋 Goodbye!")
    return True  # Signal to exit


async def _cmd_events(ex: 'DslExecutor', args: str) -> bool:
    """Show all events in store."""
    print(json.dumps(ex.event_store.get_all(), indent=2))
    return False


async def _cmd_clear(ex: 'DslExecutor', args: str) -> bool:
    """Clear event store."""
    ex.event_store.clear()
    print("🗑️ Event store cleared")
    return False


async def _cmd_connect(ex: 'DslExecutor', args: str) -> bool:
    """Connect to browser WebSocket."""
    url = args.strip() or "ws://localhost:8104/events"
    await ex.connect_websocket(url)
    return False


async def _cmd_disconnect(ex: 'DslExecutor', args: str) -> bool:
    """Disconnect from browser."""
    await ex.disconnect_websocket()
    return False


async def _cmd_run(ex: 'DslExecutor', args: str) -> bool:
    """Run a script file."""
    if not args:
        print("Usage: .run path/to/script.dsl")
        return False
    
    script_path = args.strip()
    # Handle FILE=path format
    if script_path.upper().startswith('FILE='):
        script_path = script_path[5:]
    
    if os.path.isfile(script_path):
        print(f"▶️ Running: {script_path}")
        with open(script_path, 'r') as f:
            script = f.read()
        await ex.execute_script(script)
        print(f"✅ Completed: {script_path}")
    else:
        print(f"❌ File not found: {script_path}")
    return False


async def _cmd_scripts(ex: 'DslExecutor', args: str) -> bool:
    """List available scripts."""
    examples_dir = Path(__file__).parent.parent / 'examples'
    if examples_dir.exists():
        print("📁 Available scripts:")
        for f in sorted(examples_dir.glob('*.dsl')):
            print(f"   {f.relative_to(Path(__file__).parent.parent)}")
    return False


# Register all commands
SHELL_COMMANDS.register('.exit', _cmd_exit, ['.quit', 'exit', 'quit'])
SHELL_COMMANDS.register('.events', _cmd_events)
SHELL_COMMANDS.register('.clear', _cmd_clear)
SHELL_COMMANDS.register('.connect', _cmd_connect)
SHELL_COMMANDS.register('.disconnect', _cmd_disconnect)
SHELL_COMMANDS.register('.run', _cmd_run, ['run', 'run-script'])
SHELL_COMMANDS.register('.scripts', _cmd_scripts, ['.ls'])


# ============================================================================
# Interactive Shell
# ============================================================================

async def run_shell():
    """Run interactive DSL shell"""
    executor = DslExecutor()
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║              🚀 DSL Shell - Event Sourcing CLI              ║
║                                                             ║
║  Type HELP for commands, .connect to sync with browser      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Try to connect to browser
    await executor.connect_websocket()
    
    while True:
        try:
            line = input("\n\033[1;36mdsl>\033[0m ").strip()
            
            if not line:
                continue
            
            # Try shell commands first
            handler, rest = SHELL_COMMANDS.get_handler(line)
            if handler:
                should_exit = await handler(executor, rest)
                if should_exit:
                    break
                continue
            
            # Execute DSL command
            await executor.execute(line)
            
        except KeyboardInterrupt:
            print("\n⚠️  Use .exit to quit")
        except EOFError:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

async def run_script(filename: str):
    """Execute DSL script file"""
    executor = DslExecutor()
    
    await executor.connect_websocket()
    
    with open(filename, 'r') as f:
        script = f.read()
        
    print(f"▶️ Executing: {filename}")
    await executor.execute_script(script)
    print(f"✅ Completed: {filename}")
    
    await executor.disconnect_websocket()

async def run_command(command: str):
    """Execute single command"""
    executor = DslExecutor()
    await executor.connect_websocket()
    await executor.execute(command)
    await executor.disconnect_websocket()

# ============================================================================
# Main
# ============================================================================

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '-c' and len(sys.argv) > 2:
            # Execute single command
            asyncio.run(run_command(sys.argv[2]))
        elif os.path.isfile(sys.argv[1]):
            # Execute script file
            asyncio.run(run_script(sys.argv[1]))
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: dsl-shell.py [script.dsl | -c 'COMMAND']")
    else:
        # Interactive mode
        asyncio.run(run_shell())

if __name__ == '__main__':
    main()

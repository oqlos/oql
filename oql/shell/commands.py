"""Shell command registry and interactive handlers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List

if TYPE_CHECKING:
    from .executor import DslExecutor

ShellHandler = Callable[['DslExecutor', str], Awaitable[bool]]


class ShellCommandRegistry:
    """Registry for interactive shell commands."""
    
    def __init__(self):
        self.handlers: Dict[str, ShellHandler] = {}
        self.aliases: Dict[str, str] = {}
    
    def register(self, name: str, handler: ShellHandler, aliases: List[str] | None = None):
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
        
        canonical = self.aliases.get(cmd, cmd)
        handler = self.handlers.get(canonical)
        return handler, rest


# Global registry
SHELL_COMMANDS = ShellCommandRegistry()


# ── Command handlers ───────────────────────────────────────────────

async def _cmd_exit(ex: 'DslExecutor', args: str) -> bool:
    await ex.disconnect_websocket()
    print("👋 Goodbye!")
    return True


async def _cmd_events(ex: 'DslExecutor', args: str) -> bool:
    print(json.dumps(ex.event_store.get_all(), indent=2))
    return False


async def _cmd_clear(ex: 'DslExecutor', args: str) -> bool:
    ex.event_store.clear()
    print("🗑️ Event store cleared")
    return False


async def _cmd_connect(ex: 'DslExecutor', args: str) -> bool:
    url = args.strip() or "ws://localhost:8104/events"
    await ex.connect_websocket(url)
    return False


async def _cmd_disconnect(ex: 'DslExecutor', args: str) -> bool:
    await ex.disconnect_websocket()
    return False


async def _cmd_run(ex: 'DslExecutor', args: str) -> bool:
    if not args:
        print("Usage: .run path/to/script.dsl")
        return False
    
    script_path = args.strip()
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
    examples_dir = Path(__file__).parent.parent.parent / 'examples'
    if examples_dir.exists():
        print("📁 Available scripts:")
        for f in sorted(examples_dir.glob('*.dsl')):
            print(f"   {f.relative_to(Path(__file__).parent.parent.parent)}")
    return False


async def _cmd_list(ex: 'DslExecutor', args: str) -> bool:
    """List peripherals - filter by pattern like 'pompa*' or 'pump*'"""
    import httpx
    try:
        resp = httpx.get("http://localhost:8202/api/v1/peripherals", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        pattern = args.strip().lower() if args else ""
        peripherals = data.get('peripherals', [])
        print("🔌 Peripherals:")
        found = False
        for p in peripherals:
            name = p.get('name', '')
            pid = p.get('id', '')
            current = p.get('currentValue', 'N/A')
            target = p.get('targetValue', 'N/A')
            if not pattern or pattern in name.lower() or pattern in pid.lower() or (pattern.endswith('*') and (name.lower().startswith(pattern[:-1]) or pid.lower().startswith(pattern[:-1]))):
                print(f"  {pid:20s} {name:20s} current={current} target={target}")
                found = True
        if not found:
            print("  (no matching peripherals)")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False


# Register all commands
SHELL_COMMANDS.register('.exit', _cmd_exit, ['.quit', 'exit', 'quit'])
SHELL_COMMANDS.register('.list', _cmd_list, ['list', 'ls-periph'])
SHELL_COMMANDS.register('.events', _cmd_events)
SHELL_COMMANDS.register('.clear', _cmd_clear)
SHELL_COMMANDS.register('.connect', _cmd_connect)
SHELL_COMMANDS.register('.disconnect', _cmd_disconnect)
SHELL_COMMANDS.register('.run', _cmd_run, ['run', 'run-script'])
SHELL_COMMANDS.register('.scripts', _cmd_scripts, ['.ls'])

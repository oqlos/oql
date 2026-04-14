"""Shell runner — interactive shell, script execution, CLI entry point."""

from __future__ import annotations

import asyncio
import os
import readline  # noqa: F401 — enables readline in input()
import sys

from .commands import SHELL_COMMANDS
from .executor import DslExecutor


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
    
    await executor.connect_websocket()
    
    while True:
        try:
            line = input("\n\033[1;36mdsl>\033[0m ").strip()
            
            if not line:
                continue
            
            handler, rest = SHELL_COMMANDS.get_handler(line)
            if handler:
                should_exit = await handler(executor, rest)
                if should_exit:
                    break
                continue
            
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


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '-c' and len(sys.argv) > 2:
            asyncio.run(run_command(sys.argv[2]))
        elif os.path.isfile(sys.argv[1]):
            asyncio.run(run_script(sys.argv[1]))
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: dsl-shell.py [script.dsl | -c 'COMMAND']")
    else:
        asyncio.run(run_shell())

#!/usr/bin/env python3
"""DSL CLI - Execute DSL scripts from command line."""

from __future__ import annotations

import sys
import os
import re
import json
import time
import argparse
import requests
from typing import Any
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_BASE_URL = os.getenv('DSL_API_URL', 'http://localhost:8000')
CORRELATION_ID = f"dsl-cli-{int(time.time())}"
DEFAULT_TIMEOUT_SECONDS = 30
MS_PER_SECOND = 1000
MAX_OUTPUT_LENGTH = 200

@dataclass
class DslCommand:
    type: str
    target: str
    params: dict | None = None
    expected: str | None = None
    comment: str | None = None

@dataclass
class ExecutionResult:
    success: bool
    command: DslCommand
    result: Any = None
    error: str | None = None
    duration_ms: int = 0

# =============================================================================
# PARSER
# =============================================================================

def parse_line(line: str) -> DslCommand | None:
    """Parse a single DSL line"""
    trimmed = line.strip()
    
    # Skip empty lines and comments
    if not trimmed or trimmed.startswith('#'):
        return None

    # API command: API GET "/url" {"body": {...}}
    api_match = re.match(
        r'^API\s+(GET|POST|PUT|DELETE|PATCH)\s+"([^"]+)"(?:\s+(\{.+\}))?(?:\s*->\s*(\w+))?(?:\s*#\s*(.*))?$',
        trimmed
    )
    if api_match:
        method, url, params_str, expected, comment = api_match.groups()
        params = json.loads(params_str) if params_str else {}
        params['method'] = method
        return DslCommand('API', url, params, expected, comment)

    # WAIT command
    wait_match = re.match(r'^WAIT\s+(\d+)(?:\s*#\s*(.*))?$', trimmed)
    if wait_match:
        ms, comment = wait_match.groups()
        return DslCommand('WAIT', ms, None, None, comment)

    # General format: COMMAND "target" {params} -> expected # comment
    general_match = re.match(
        r'^(\w+)\s+"([^"]+)"(?:\s+(\{[^}]+\}))?(?:\s*->\s*(\w+))?(?:\s*#\s*(.*))?$',
        trimmed
    )
    if general_match:
        cmd_type, target, params_str, expected, comment = general_match.groups()
        params = json.loads(params_str) if params_str else None
        return DslCommand(cmd_type.upper(), target, params, expected, comment)

    # Simple command without quotes
    simple_match = re.match(r'^(\w+)\s+(.+?)(?:\s*#\s*(.*))?$', trimmed)
    if simple_match:
        cmd_type, target, comment = simple_match.groups()
        return DslCommand(cmd_type.upper(), target.strip(), None, None, comment)

    print(f"⚠️  Invalid DSL line: {line}", file=sys.stderr)
    return None

def parse_script(content: str) -> list[DslCommand]:
    """Parse DSL script into commands"""
    return [cmd for line in content.split('\n') if (cmd := parse_line(line))]

# =============================================================================
# EXECUTOR
# =============================================================================

class DslCliExecutor:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.context: dict[str, Any] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Correlation-Id': CORRELATION_ID,
        })

    def execute(self, cmd: DslCommand) -> ExecutionResult:
        """Execute a single command"""
        start = time.perf_counter()
        
        try:
            result = self._dispatch(cmd)
            duration = int((time.perf_counter() - start) * 1000)
            return ExecutionResult(True, cmd, result, None, duration)
        except Exception as e:
            duration = int((time.perf_counter() - start) * 1000)
            return ExecutionResult(False, cmd, None, str(e), duration)

    # Browser-only commands (skip in CLI)
    BROWSER_COMMANDS = {'NAVIGATE', 'CLICK', 'SELECT', 'INPUT', 'SUBMIT'}
    
    # Semantic commands (skip in CLI, log only)
    SEMANTIC_COMMANDS = {
        'SELECT_DEVICE', 'SELECT_INTERVAL', 'START_TEST', 'STEP_COMPLETE',
        'PROTOCOL_CREATED', 'PROTOCOL_FINALIZE', 'OPEN_INTERVAL_DIALOG',
        'TEST_RUN_PARAMS', 'SESSION_START', 'SESSION_END',
        # App lifecycle
        'APP_START', 'APP_INIT', 'APP_READY', 'APP_ERROR',
        # Module lifecycle
        'MODULE_LOAD', 'MODULE_READY', 'MODULE_ERROR',
        # Page lifecycle
        'PAGE_SETUP', 'PAGE_ERROR', 'PAGE_RENDER',
        # Report actions
        'REPORT_AUTOOPEN', 'REPORT_FETCH', 'REPORT_OPEN', 'REPORT_ERROR', 'REPORT_PRINT', 'REPORT_LIST',
        # Protocol operations
        'PROTOCOL_FETCH', 'PROTOCOL_LOAD', 'PROTOCOL_PARSE', 'PROTOCOL_NORMALIZE', 'PROTOCOL_FILTER', 'PROTOCOL_ERROR',
    }

    def _dispatch(self, cmd: DslCommand) -> Any:
        """Dispatch command to handler"""
        # Skip browser-only commands
        if cmd.type in self.BROWSER_COMMANDS:
            if self.verbose:
                print("   └─ [BROWSER] Skipped (browser-only command)")
            return {'skipped': True, 'reason': 'browser-only'}
        
        # Log semantic commands but don't execute
        if cmd.type in self.SEMANTIC_COMMANDS:
            if self.verbose:
                print("   └─ [SEMANTIC] Logged (high-level action)")
            return {'logged': True, 'action': cmd.type}
        
        handler = getattr(self, f'cmd_{cmd.type.lower()}', None)
        if not handler:
            raise ValueError(f"Unknown command: {cmd.type}")
        return handler(cmd)

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def cmd_api(self, cmd: DslCommand) -> dict:
        """Make API request"""
        method = cmd.params.get('method', 'GET') if cmd.params else 'GET'
        url = cmd.target if cmd.target.startswith('http') else f"{self.base_url}{cmd.target}"
        body = cmd.params.get('body') if cmd.params else None
        headers = cmd.params.get('headers', {}) if cmd.params else {}

        response = self.session.request(
            method=method,
            url=url,
            json=body,
            headers=headers,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

        try:
            data = response.json()
        except Exception:
            data = response.text

        self.context['$response'] = data
        self.context['$status'] = response.status_code
        self.context['$headers'] = dict(response.headers)

        if not response.ok:
            raise ValueError(f"HTTP {response.status_code}: {data}")

        return data

    def cmd_wait(self, cmd: DslCommand) -> None:
        """Wait for specified milliseconds"""
        ms = int(cmd.target)
        time.sleep(ms / MS_PER_SECOND)

    def cmd_log(self, cmd: DslCommand) -> None:
        """Log a message"""
        level = cmd.params.get('level', 'info') if cmd.params else 'info'
        print(f"[{level.upper()}] {cmd.target}")

    def cmd_print(self, cmd: DslCommand) -> Any:
        """Print a context variable"""
        value = self.context.get(cmd.target, f"<undefined: {cmd.target}>")
        print(json.dumps(value, indent=2) if isinstance(value, (dict, list)) else value)
        return value

    def cmd_store(self, cmd: DslCommand) -> None:
        """Store a value in context"""
        value = cmd.params.get('value') if cmd.params else None
        self.context[cmd.target] = value

    def cmd_env(self, cmd: DslCommand) -> str:
        """Get environment variable"""
        default = cmd.params.get('default') if cmd.params else None
        value = os.getenv(cmd.target, default)
        self.context[f'${cmd.target}'] = value
        return value

    def cmd_assert_status(self, cmd: DslCommand) -> bool:
        """Assert HTTP status code"""
        expected = int(cmd.target)
        actual = self.context.get('$status')
        if actual != expected:
            raise AssertionError(f"Status mismatch: expected {expected}, got {actual}")
        return True

    def cmd_assert_json(self, cmd: DslCommand) -> bool:
        """Assert JSON path value (simple implementation)"""
        from functools import reduce
        
        path = cmd.target
        response = self.context.get('$response', {})
        
        # Simple JSONPath: $.data[0].id -> ['data', 0, 'id']
        parts = path.replace('$', '').strip('.').replace('[', '.').replace(']', '').split('.')
        parts = [int(p) if p.isdigit() else p for p in parts if p]
        
        try:
            value = reduce(lambda obj, key: obj[key], parts, response)
        except (KeyError, IndexError, TypeError):
            raise AssertionError(f"Path not found: {path}")

        if cmd.params:
            if 'equals' in cmd.params and value != cmd.params['equals']:
                raise AssertionError(f"Value mismatch at {path}: expected {cmd.params['equals']}, got {value}")
            if 'contains' in cmd.params and cmd.params['contains'] not in str(value):
                raise AssertionError(f"Value at {path} does not contain {cmd.params['contains']}")
            if 'type' in cmd.params and type(value).__name__ != cmd.params['type']:
                raise AssertionError(f"Type mismatch at {path}: expected {cmd.params['type']}, got {type(value).__name__}")

        return True

    def cmd_set_header(self, cmd: DslCommand) -> None:
        """Set HTTP header for subsequent requests"""
        value = cmd.params.get('value', '') if cmd.params else ''
        self.session.headers[cmd.target] = value

    def cmd_set_base_url(self, cmd: DslCommand) -> None:
        """Change base URL"""
        self.base_url = cmd.target.rstrip('/')

    # =========================================================================
    # SCRIPT EXECUTION
    # =========================================================================

    def run_script(self, content: str, stop_on_error: bool = True) -> list[ExecutionResult]:
        """Execute a DSL script"""
        commands = parse_script(content)
        results: list[ExecutionResult] = []

        print(f"▶️  DSL Script: {len(commands)} commands")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🔗 Correlation ID: {CORRELATION_ID}")
        print("-" * 50)

        for i, cmd in enumerate(commands, 1):
            result = self.execute(cmd)
            results.append(result)

            # Choose icon based on command type and result
            if cmd.type in self.BROWSER_COMMANDS:
                icon = '🌐'  # Browser command
            elif cmd.type in self.SEMANTIC_COMMANDS:
                icon = '📋'  # Semantic command
            elif result.success:
                icon = '✅'
            else:
                icon = '❌'
            
            duration = f"{result.duration_ms}ms"
            print(f"{icon} [{i}/{len(commands)}] {self._format_cmd(cmd)} ({duration})")

            if self.verbose and result.result:
                print(f"   └─ {json.dumps(result.result, indent=2)[:MAX_OUTPUT_LENGTH]}")

            if not result.success:
                print(f"   └─ Error: {result.error}")
                if stop_on_error:
                    print("⛔ Stopped on error")
                    break

        print("-" * 50)
        passed = sum(1 for r in results if r.success)
        print(f"⏹️  Completed: {passed}/{len(results)} passed")

        return results

    def _format_cmd(self, cmd: DslCommand) -> str:
        """Format command for display"""
        params = f" {json.dumps(cmd.params)}" if cmd.params else ""
        return f'{cmd.type} "{cmd.target}"{params}'

# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description='DSL CLI - Execute DSL scripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('file', nargs='?', default='-', help='DSL script file (or - for stdin)')
    parser.add_argument('-c', '--command', help='Execute single command')
    parser.add_argument('-u', '--url', '--api-url', default=DEFAULT_BASE_URL, 
                        dest='url', help='Base API URL (e.g., http://localhost:8101)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--continue', dest='continue_on_error', action='store_true', 
                        help='Continue on error')
    
    args = parser.parse_args()
    
    executor = DslCliExecutor(base_url=args.url, verbose=args.verbose)

    # Single command mode
    if args.command:
        cmd = parse_line(args.command)
        if cmd:
            result = executor.execute(cmd)
            icon = '✅' if result.success else '❌'
            print(f"{icon} {executor._format_cmd(cmd)} ({result.duration_ms}ms)")
            if result.result:
                print(json.dumps(result.result, indent=2))
            if result.error:
                print(f"Error: {result.error}")
            sys.exit(0 if result.success else 1)
        else:
            print("Invalid command", file=sys.stderr)
            sys.exit(1)

    # Script mode
    if args.file == '-':
        content = sys.stdin.read()
    else:
        with open(args.file, 'r') as f:
            content = f.read()

    results = executor.run_script(content, stop_on_error=not args.continue_on_error)
    
    # Exit code: 0 if all passed, 1 otherwise
    sys.exit(0 if all(r.success for r in results) else 1)

if __name__ == '__main__':
    main()

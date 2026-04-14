#!/usr/bin/env python3
"""
Connex Shell — Unified CLI for CQL and IQL languages.

Usage:
  python connex-shell.py                           # Interactive REPL
  python connex-shell.py script.cql                # Execute CQL scenario
  python connex-shell.py script.iql                # Execute IQL script
  python connex-shell.py -c "API GET /api/v3/..."  # Single IQL command
  python connex-shell.py --validate db/dsl/cql/    # Validate CQL directory

The shell auto-detects language by file extension (.cql / .iql).
In interactive mode, CQL commands (GOAL, SCENARIO, etc.) and IQL commands
(NAVIGATE, API, SET, etc.) can be mixed freely.
"""

from __future__ import annotations

import json
import os
import readline
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "dsl"))

from interpreter.base import EventBridge, InterpreterOutput, ScriptResult, VariableStore
from interpreter.cql import CqlInterpreter, parse_cql, validate_cql
from interpreter.iql import IqlInterpreter

# ═══════════════════════════════════════════════════════════════════════════════
# Shell
# ═══════════════════════════════════════════════════════════════════════════════

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║              🚀 Connex Shell — CQL + IQL Runtime              ║
║                                                               ║
║  CQL: scenariusze testowe urządzeń        (.cql)              ║
║  IQL: sterowanie GUI, testy API           (.iql)              ║
║                                                               ║
║  Wpisz .help aby zobaczyć komendy                             ║
╚═══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
📋 Connex Shell — komendy:

─── Pliki ───────────────────────────────────────────────────
  .run <plik.cql|iql>        Uruchom skrypt
  .validate <plik.cql>       Waliduj plik CQL
  .validate-dir <katalog>    Waliduj wszystkie .cql w katalogu
  .ls [katalog]              Lista plików DSL
  .cat <plik>                Pokaż zawartość pliku

─── Zmienne ─────────────────────────────────────────────────
  SET <nazwa> <wartość>      Ustaw zmienną
  GET <nazwa>                Pokaż zmienną
  .vars                      Pokaż wszystkie zmienne

─── API (IQL) ───────────────────────────────────────────────
  API GET <url>              Zapytanie GET
  API POST <url> {...}       Zapytanie POST z body
  ASSERT_STATUS <kod>        Sprawdź status odpowiedzi
  ASSERT_CONTAINS "text"     Sprawdź zawartość odpowiedzi
  ASSERT_JSON <path> <op> <val>  Sprawdź JSON

─── CQL (scenariusze) ──────────────────────────────────────
  .cql <plik.cql>            Uruchom scenariusz CQL (dry-run)
  .cql-exec <plik.cql>       Uruchom scenariusz CQL (execute)
  .cql-info <plik.cql>       Pokaż informacje o scenariuszu

─── Nawigacja (IQL) ─────────────────────────────────────────
  NAVIGATE "/route"          Nawiguj do trasy
  CLICK "#selector"          Kliknij element
  SELECT_DEVICE "id" {...}   Wybierz urządzenie
  START_TEST "scenario" {...} Uruchom test
  LOG "wiadomość"            Wypisz wiadomość
  WAIT <ms>                  Poczekaj (milisekundy)

─── Shell ───────────────────────────────────────────────────
  .help                      Ta pomoc
  .history                   Historia poleceń
  .clear                     Wyczyść ekran
  .exit / .quit              Wyjście
"""

_EVENT_TYPE_MAP = {
    "NAVIGATE": "navigation.navigated",
    "CLICK": "ui.button_clicked",
    "INPUT": "ui.input_changed",
    "SELECT_DEVICE": "test.device_selected",
    "SELECT_INTERVAL": "test.interval_selected",
    "START_TEST": "test.started",
    "STEP_COMPLETE": "test.step_executed",
    "PROTOCOL_CREATED": "protocol.created",
    "PROTOCOL_FINALIZE": "protocol.finalized",
    "EMIT": "custom.event",
    "RENDER": "component.render_requested",
    "LAYOUT": "layout.changed",
    "RECORD_START": "session.started",
    "RECORD_STOP": "session.ended",
}

def _iql_cmd_to_event_type(cmd: str) -> str:
    return _EVENT_TYPE_MAP.get(cmd, f"iql.{cmd.lower()}")

class ConnexShell:
    """Unified interactive shell for CQL and IQL."""

    def __init__(self, api_url: str = "http://localhost:8101", ws_url: str = "ws://localhost:8104/cli"):
        self.api_url = api_url
        self.ws_url = ws_url
        self.vars = VariableStore()
        self.out = InterpreterOutput()
        self.iql: IqlInterpreter | None = None
        self.bridge = EventBridge(url=ws_url)
        self.history: list[str] = []
        self.dsl_root = _root / "db" / "dsl"
        self._setup_readline()

    def _setup_readline(self):
        """Configure readline for tab completion and history."""
        histfile = Path.home() / ".connex_shell_history"
        try:
            readline.read_history_file(str(histfile))
        except FileNotFoundError:
            pass
        readline.set_history_length(500)

        import atexit
        atexit.register(readline.write_history_file, str(histfile))

        readline.set_completer(self._completer)
        readline.parse_and_bind("tab: complete")

    def _completer(self, text: str, state: int) -> str | None:
        """Tab completion for commands and file paths."""
        commands = [
            ".run", ".validate", ".validate-dir", ".ls", ".cat", ".vars",
            ".cql", ".cql-exec", ".cql-info", ".help", ".history", ".clear",
            ".exit", ".quit",
            "SET", "GET", "API", "ASSERT_STATUS", "ASSERT_CONTAINS",
            "ASSERT_JSON", "ASSERT_OK", "NAVIGATE", "CLICK", "INPUT",
            "SELECT_DEVICE", "SELECT_INTERVAL", "START_TEST", "WAIT", "LOG",
            "INCLUDE", "EMIT",
        ]
        matches = [c for c in commands if c.lower().startswith(text.lower())]
        return matches[state] if state < len(matches) else None

    def _get_iql(self) -> IqlInterpreter:
        """Get or create IQL interpreter, sharing variables."""
        if not self.iql:
            self.iql = IqlInterpreter(
                api_url=self.api_url,
                variables=self.vars.all(),
                include_paths=[str(self.dsl_root / "iql"), "."],
            )
        else:
            # Sync variables
            for k, v in self.vars.all().items():
                self.iql.vars.set(k, v)
        return self.iql

    def run_interactive(self) -> None:
        """Run interactive REPL."""
        print(BANNER)
        print(f"  API: {self.api_url}")
        print(f"  DSL: {self.dsl_root}")

        # Try to connect to event server for browser sync
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            connected = loop.run_until_complete(self.bridge.connect())
            if connected:
                print(f"  🔌 Browser sync: {self.ws_url}")
            else:
                print(f"  ⚠️  Browser sync: not available (event server not running)")
        except Exception:
            print(f"  ⚠️  Browser sync: not available")
        print()

        while True:
            try:
                line = input("\033[1;36mconnex>\033[0m ").strip()
                if not line:
                    continue
                self.history.append(line)
                self._process_line(line)
            except KeyboardInterrupt:
                print("\n⚠️  Użyj .exit aby wyjść")
            except EOFError:
                break

        print("👋 Do zobaczenia!")

    def _process_line(self, line: str) -> None:
        """Process a single input line."""

        # ── Shell commands (.xxx) ──
        if line.startswith("."):
            self._shell_command(line)
            return

        # ── Comment ──
        if line.startswith("#"):
            return

        # ── SET / GET ──
        parts = line.split(None, 1)
        cmd = parts[0].upper()

        if cmd == "SET":
            args = parts[1] if len(parts) > 1 else ""
            kv = args.split(None, 1)
            if len(kv) >= 2:
                key, val = kv[0], kv[1].strip().strip('"\'')
                self.vars.set(key, val)
                print(f"📝 {key} = {val}")
            else:
                print("Usage: SET <name> <value>")
            return

        if cmd == "GET":
            key = (parts[1] if len(parts) > 1 else "").strip()
            val = self.vars.get(key, "<undefined>")
            print(f"📖 {key} = {val}")
            return

        # ── IQL command (API, ASSERT, NAVIGATE, etc.) ──
        iql = self._get_iql()
        from interpreter.iql import IqlLine
        iql_line = IqlLine(number=0, command=cmd, args=parts[1] if len(parts) > 1 else "", raw=line)
        args_interp = self.vars.interpolate(iql_line.args)
        try:
            iql._dispatch(cmd, args_interp, iql_line)
        except Exception as e:
            print(f"❌ {e}")

        # Broadcast event to browser via WebSocket bridge
        if self.bridge.connected and iql.events:
            import asyncio
            last_event = iql.events[-1]
            event_type = _iql_cmd_to_event_type(cmd)
            payload = {"args": args_interp}
            if cmd == "NAVIGATE":
                payload = {"route": args_interp.strip().strip("\"'")}
            elif cmd in ("CLICK", "INPUT"):
                payload = {"selector": args_interp.strip().strip("\"'")}
            elif cmd == "SELECT_DEVICE":
                payload = {"deviceId": args_interp.split()[0].strip("\"'")} if args_interp else {}
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(self.bridge.send_event(event_type, payload))
            except Exception:
                pass

        # Sync variables back
        for k, v in iql.vars.all().items():
            self.vars.set(k, v)

    def _shell_command(self, line: str) -> None:
        """Handle .xxx shell commands."""
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in (".exit", ".quit"):
            raise EOFError

        if cmd == ".help":
            print(HELP_TEXT)

        elif cmd == ".clear":
            os.system("clear" if os.name != "nt" else "cls")

        elif cmd == ".vars":
            all_vars = self.vars.all()
            if all_vars:
                for k, v in sorted(all_vars.items()):
                    print(f"  {k} = {v}")
            else:
                print("  (brak zmiennych)")

        elif cmd == ".history":
            for i, h in enumerate(self.history[-20:], 1):
                print(f"  {i:3}  {h}")

        elif cmd == ".run":
            self._run_file(args)

        elif cmd == ".validate":
            self._validate_file(args)

        elif cmd == ".validate-dir":
            self._validate_dir(args)

        elif cmd == ".cql":
            self._run_cql(args, mode="dry-run")

        elif cmd == ".cql-exec":
            self._run_cql(args, mode="execute")

        elif cmd == ".cql-info":
            self._cql_info(args)

        elif cmd == ".ls":
            self._list_files(args)

        elif cmd == ".cat":
            self._cat_file(args)

        else:
            print(f"❓ Nieznana komenda: {cmd}")
            print("   Wpisz .help aby zobaczyć listę komend")

    # ── File operations ──────────────────────────────────────────────────

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to dsl_root or cwd."""
        p = Path(path)
        if p.is_absolute():
            return p
        # Try relative to cwd first
        if p.exists():
            return p.resolve()
        # Try relative to dsl_root
        candidate = self.dsl_root / p
        if candidate.exists():
            return candidate.resolve()
        # Try relative to project root
        candidate = _root / p
        if candidate.exists():
            return candidate.resolve()
        return p.resolve()

    def _run_file(self, path: str) -> None:
        """Run a .cql or .iql file."""
        if not path:
            print("Usage: .run <file.cql|iql>")
            return

        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return

        ext = resolved.suffix.lower()
        if ext == ".cql":
            self._run_cql(str(resolved), mode="dry-run")
        elif ext in (".iql", ".dsl"):
            self._run_iql(str(resolved))
        else:
            print(f"⚠️  Nieznane rozszerzenie: {ext}. Próbuję jako IQL...")
            self._run_iql(str(resolved))

    def _run_cql(self, path: str, mode: str = "dry-run") -> None:
        if not path:
            print("Usage: .cql <file.cql>")
            return
        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return

        # Collect sensor values from variables
        sensors: dict[str, float] = {}
        for k, v in self.vars.all().items():
            if k.startswith("AI") or k.startswith("Timer"):
                try:
                    sensors[k] = float(v)
                except (ValueError, TypeError):
                    pass

        interp = CqlInterpreter(mode=mode, variables=self.vars.all(), sensor_values=sensors)
        result = interp.run_file(str(resolved))
        # Sync variables back
        for k, v in result.variables.items():
            self.vars.set(k, v)

    def _run_iql(self, path: str) -> None:
        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return

        interp = IqlInterpreter(
            api_url=self.api_url, variables=self.vars.all(),
            include_paths=[str(resolved.parent), str(self.dsl_root / "iql"), "."],
        )
        result = interp.run_file(str(resolved))
        for k, v in result.variables.items():
            self.vars.set(k, v)

    def _validate_file(self, path: str) -> None:
        if not path:
            print("Usage: .validate <file.cql>")
            return
        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return

        interp = CqlInterpreter(mode="validate", quiet=True)
        result = interp.run_file(str(resolved))
        issues = len(result.warnings) + len(result.errors)
        if issues == 0:
            print(f"✅ {resolved.name}: OK")
        else:
            print(f"⚠️  {resolved.name}: {issues} issue(s)")
            for w in result.warnings:
                print(f"  ⚠️  {w}")
            for e in result.errors:
                print(f"  ❌ {e}")

    def _validate_dir(self, path: str) -> None:
        if not path:
            path = str(self.dsl_root / "cql")
        resolved = self._resolve_path(path)
        if not resolved.is_dir():
            print(f"❌ Katalog nie znaleziony: {path}")
            return

        files = sorted(resolved.rglob("*.cql"))
        if not files:
            print(f"Brak plików .cql w {resolved}")
            return

        total_issues = 0
        for f in files:
            interp = CqlInterpreter(mode="validate", quiet=True)
            result = interp.run_file(str(f))
            issues = len(result.warnings) + len(result.errors)
            total_issues += issues
            icon = "✅" if issues == 0 else "⚠️ "
            print(f"  {icon} {f.relative_to(resolved)}: {issues}")

        icon = "✅" if total_issues == 0 else "⚠️ "
        print(f"\n{icon} {len(files)} plików, {total_issues} issues")

    def _cql_info(self, path: str) -> None:
        if not path:
            print("Usage: .cql-info <file.cql>")
            return
        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return

        source = resolved.read_text(encoding="utf-8")
        doc = parse_cql(source, str(resolved.name))

        print(f"\n📋 {doc.metadata.scenario_name or resolved.name}")
        if doc.metadata.device_type:
            print(f"  🔧 Urządzenie: {doc.metadata.device_type}")
        if doc.metadata.device_model:
            print(f"  📦 Model: {doc.metadata.device_model}")
        if doc.metadata.manufacturer:
            print(f"  🏭 Producent: {doc.metadata.manufacturer}")
        if doc.intervals:
            print(f"  ⏱️  Interwały: {len(doc.intervals)}")
            for iv in doc.intervals:
                print(f"     {iv.code}: {iv.label} ({iv.period_months}m)")

        all_goals = list(doc.goals)
        for sc in doc.scenarios:
            print(f"\n  📂 @{sc.namespace}.{sc.name}" if sc.namespace else f"\n  📂 @{sc.name}")
            if sc.description:
                print(f"     {sc.description}")
            if sc.intervals:
                print(f"     intervals: [{', '.join(sc.intervals)}]")
            all_goals.extend(sc.goals)

        print(f"\n  🎯 Goals: {len(all_goals)}")
        total_steps = 0
        for g in all_goals:
            step_count = len(g.steps)
            total_steps += step_count
            action_count = sum(len(s.actions) for s in g.steps)
            print(f"     • {g.name}: {step_count} steps, {action_count} actions")

        issues = validate_cql(doc)
        if issues:
            print(f"\n  ⚠️  Issues: {len(issues)}")
            for issue in issues:
                print(f"     • {issue}")

        print(f"\n  📊 Razem: {len(all_goals)} goals, {total_steps} steps")
        if doc.warnings:
            print(f"  ⚠️  Parser warnings: {len(doc.warnings)}")

    def _list_files(self, path: str) -> None:
        target = self._resolve_path(path) if path else self.dsl_root
        if not target.is_dir():
            print(f"❌ Katalog nie znaleziony: {path or str(self.dsl_root)}")
            return

        cql_files = sorted(target.rglob("*.cql"))
        iql_files = sorted(target.rglob("*.iql"))
        connectgo_files = sorted(target.rglob("*.connectgo"))

        if cql_files:
            print(f"\n📂 CQL ({len(cql_files)} plików):")
            for f in cql_files:
                size = f.stat().st_size
                print(f"  {f.relative_to(target)}  ({size:,} B)")

        if iql_files:
            print(f"\n📂 IQL ({len(iql_files)} plików):")
            for f in iql_files:
                size = f.stat().st_size
                print(f"  {f.relative_to(target)}  ({size:,} B)")

        if connectgo_files:
            print(f"\n📂 ConnectGo ({len(connectgo_files)} plików):")
            for f in connectgo_files:
                size = f.stat().st_size
                print(f"  {f.relative_to(target)}  ({size:,} B)")

        total = len(cql_files) + len(iql_files) + len(connectgo_files)
        if total == 0:
            print("  (brak plików DSL)")
        else:
            print(f"\n  Razem: {total} plików")

    def _cat_file(self, path: str) -> None:
        if not path:
            print("Usage: .cat <file>")
            return
        resolved = self._resolve_path(path)
        if not resolved.is_file():
            print(f"❌ Plik nie znaleziony: {path}")
            return
        content = resolved.read_text(encoding="utf-8")
        for i, line in enumerate(content.split("\n"), 1):
            print(f"  {i:4} │ {line}")

# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Connex Shell — Unified CQL + IQL Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Interactive shell
  %(prog)s db/dsl/cql/scenarios/mask.cql      Run CQL scenario (dry-run)
  %(prog)s db/dsl/iql/tests/test-api.iql      Run IQL script
  %(prog)s -c "API GET /api/v3/data/devices"  Single IQL command
  %(prog)s --validate-dir db/dsl/cql/         Validate all CQL files
        """,
    )
    parser.add_argument("file", nargs="?", help="Script file (.cql or .iql)")
    parser.add_argument("-c", "--command", help="Execute single IQL command")
    parser.add_argument("-u", "--url", default="http://localhost:8101",
                        help="Backend API URL (default: http://localhost:8101)")
    parser.add_argument("--validate", help="Validate a CQL file")
    parser.add_argument("--validate-dir", help="Validate all .cql files in directory")
    parser.add_argument("-m", "--mode", choices=["validate", "dry-run", "execute"],
                        default="dry-run", help="CQL execution mode")
    parser.add_argument("-v", "--var", action="append", default=[],
                        help="Set variable: name=value")
    parser.add_argument("-s", "--sensor", action="append", default=[],
                        help="Mock sensor value: AI01=7.5")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    # Parse variables and sensors
    variables: dict[str, Any] = {}
    for v in args.var:
        if "=" in v:
            k, val = v.split("=", 1)
            variables[k.strip()] = val.strip()

    sensors: dict[str, float] = {}
    for s in args.sensor:
        if "=" in s:
            k, val = s.split("=", 1)
            sensors[k.strip()] = float(val.strip())

    # ── Validate directory ──
    if args.validate_dir:
        shell = ConnexShell(api_url=args.url)
        shell._validate_dir(args.validate_dir)
        return

    # ── Validate single file ──
    if args.validate:
        shell = ConnexShell(api_url=args.url)
        shell._validate_file(args.validate)
        return

    # ── Single command ──
    if args.command:
        interp = IqlInterpreter(
            api_url=args.url, variables=variables, quiet=args.quiet,
        )
        result = interp.run(args.command, filename="<command>")
        if args.json:
            _print_json(result)
        exit(0 if result.ok else 1)

    # ── Execute file ──
    if args.file:
        p = Path(args.file)
        ext = p.suffix.lower()

        if ext == ".cql":
            interp = CqlInterpreter(
                mode=args.mode, variables=variables,
                quiet=args.quiet, sensor_values=sensors,
            )
        else:
            interp = IqlInterpreter(
                api_url=args.url, variables=variables,
                quiet=args.quiet,
                include_paths=[str(p.parent.resolve()), "."],
            )

        result = interp.run_file(args.file)
        if args.json:
            _print_json(result)
        exit(0 if result.ok else 1)

    # ── Interactive shell ──
    shell = ConnexShell(api_url=args.url)
    for k, v in variables.items():
        shell.vars.set(k, v)
    shell.run_interactive()

def _print_json(result: ScriptResult) -> None:
    print(json.dumps({
        "source": result.source,
        "ok": result.ok,
        "passed": result.passed,
        "failed": result.failed,
        "total": len(result.steps),
        "duration_ms": round(result.duration_ms, 1),
        "errors": result.errors,
        "warnings": result.warnings,
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

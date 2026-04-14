"""OQL CLI — oqlctl command line tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="oql")
def main() -> None:
    """oqlctl — OQL command line interface."""


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--step", is_flag=True, help="Manual step-by-step mode")
@click.option("--mode", type=click.Choice(["dry-run", "execute"]), default="dry-run")
@click.option("--firmware-url", default="http://localhost:8202")
def run(file: str, step: bool, mode: str, firmware_url: str) -> None:
    """Run an OQL scenario file."""
    from oqlos.core.interpreter import CqlInterpreter

    source = Path(file).read_text(encoding="utf-8")
    interp = CqlInterpreter(mode=mode, firmware_url=firmware_url)
    result = interp.run(source, Path(file).name)
    sys.exit(0 if result.ok else 1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file: str) -> None:
    """Validate an OQL scenario file (parse only)."""
    from oqlos.core.interpreter import CqlInterpreter

    source = Path(file).read_text(encoding="utf-8")
    interp = CqlInterpreter(mode="validate")
    result = interp.run(source, Path(file).name)
    sys.exit(0 if result.ok else 1)


@main.command()
@click.option("--url", default="http://localhost:8200", help="OqlOS API URL")
def hardware(url: str) -> None:
    """List connected hardware peripherals."""
    import httpx

    try:
        resp = httpx.get(f"{url}/api/hardware/peripherals", timeout=5)
        resp.raise_for_status()
        import json
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--url", default="http://localhost:8200", help="OqlOS API URL")
def scenarios(url: str) -> None:
    """List available scenarios."""
    import httpx

    try:
        resp = httpx.get(f"{url}/api/scenarios", timeout=5)
        resp.raise_for_status()
        for s in resp.json().get("data", []):
            click.echo(f"  {s.get('id', '?'):20s}  {s.get('name', '')}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command(name="shell")
def shell_cmd() -> None:
    """Start interactive OQL shell."""
    click.echo("OQL Shell v0.1 — type help for commands, exit to quit")
    from oql.adapters.local import LocalAdapter

    adapter = LocalAdapter()

    while True:
        try:
            line = input("oql> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nBye.")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        adapter.execute(line)


if __name__ == "__main__":
    main()

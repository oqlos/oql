"""OQL CLI — oqlctl command line tool."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="oql")
def main() -> None:
    """oqlctl — OQL command line interface."""


def _build_single_command_scenario(command: str) -> str:
    """Wrap a single OQL command line in a minimal scenario document."""
    stripped = command.strip()
    if not stripped:
        raise click.UsageError("Command cannot be empty")

    indented_command = textwrap.indent(stripped, "    ")
    return (
        'SCENARIO: "Single command"\n'
        'GOAL: Execute command\n'
        '  1. Run command:\n'
        f"{indented_command}\n"
    )


def _execute_single_command(command: str, firmware_url: str, mode: str) -> int:
    """Execute one OQL command line by wrapping it in a minimal scenario."""
    from oqlos.core.interpreter import CqlInterpreter

    source = _build_single_command_scenario(command)
    interp = CqlInterpreter(mode=mode, firmware_url=firmware_url)
    result = interp.run(source, "<cmd>")
    return 0 if result.ok else 1


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--step", is_flag=True, help="Manual step-by-step mode")
@click.option("--mode", type=click.Choice(["dry-run", "execute"]), default="execute")
@click.option("--firmware-url", default="http://localhost:8202")
@click.option("--report", type=click.Choice(["json", "junit", "html"]), default=None, help="Generate report output")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file for report")
def run(file: str, step: bool, mode: str, firmware_url: str, report: str | None, output: str | None) -> None:
    """Run an OQL scenario file."""
    from oqlos.core.interpreter import CqlInterpreter

    source = Path(file).read_text(encoding="utf-8")
    interp = CqlInterpreter(mode=mode, firmware_url=firmware_url)
    result = interp.run(source, Path(file).name)

    if report:
        report_content = _generate_report(result, report)
        if output:
            Path(output).write_text(report_content, encoding="utf-8")
            click.echo(f"Report written to {output}")
        else:
            click.echo(report_content)

    sys.exit(0 if result.ok else 1)


def _generate_report(result, fmt: str) -> str:
    """Generate report content from a ScriptResult."""
    if fmt == "json":
        from oqlos.reporters.json_reporter import report_json
        return report_json(result)
    elif fmt == "junit":
        from oqlos.reporters.junit import JUnitReporter
        return JUnitReporter().generate(result)
    elif fmt == "html":
        from oqlos.reporters.json_reporter import report_json
        from oqlos.reporters.html_report import render_html_report
        data_json = report_json(result)
        return render_html_report(data_json)
    raise click.UsageError(f"Unknown report format: {fmt}")


@main.command()
@click.argument("data_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default=None, help="Output HTML file")
def report(data_file: str, output: str | None) -> None:
    """Generate HTML report from data.json.

    Pipeline: data.json → raport.html
    """
    from oqlos.reporters.html_report import render_html_report

    data_json = Path(data_file).read_text(encoding="utf-8")
    html = render_html_report(data_json)
    if output:
        Path(output).write_text(html, encoding="utf-8")
        click.echo(f"Report written to {output}")
    else:
        click.echo(html)


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
@click.argument("command", type=str)
@click.option("--mode", type=click.Choice(["dry-run", "execute"]), default="execute")
@click.option("--firmware-url", default="http://localhost:8202")
def cmd(command: str, mode: str, firmware_url: str) -> None:
    """Execute a single OQL command line."""
    sys.exit(_execute_single_command(command, firmware_url, mode))


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

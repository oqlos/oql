"""Basic tests for OQL CLI."""

from __future__ import annotations

from click.testing import CliRunner

import oql.cli as cli
from oql.cli import main


class TestCli:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "oqlctl" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_single_command_scenario_wrapper(self):
        scenario = cli._build_single_command_scenario("SET 'pompa 1' '0'")
        assert 'SCENARIO: "Single command"' in scenario
        assert 'GOAL: Execute command' in scenario
        assert "SET 'pompa 1' '0'" in scenario

    def test_cmd_subcommand_invokes_helper(self, monkeypatch):
        captured: dict[str, str] = {}

        def fake_execute_single_command(command: str, firmware_url: str, mode: str) -> int:
            captured["command"] = command
            captured["firmware_url"] = firmware_url
            captured["mode"] = mode
            return 0

        monkeypatch.setattr(cli, "_execute_single_command", fake_execute_single_command)

        runner = CliRunner()
        result = runner.invoke(main, ["cmd", "SET 'pompa 1' '0'"])

        assert result.exit_code == 0
        assert captured == {
            "command": "SET 'pompa 1' '0'",
            "firmware_url": "http://localhost:8202",
            "mode": "execute",
        }

# OQL — Command Line Interface for OqlOS


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.1-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.30-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-5.2h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.3000 (2 commits)
- 👤 **Human dev:** ~$518 (5.2h @ $100/h, 30min dedup)

Generated on 2026-04-15 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---



OQL CLI (`oqlctl`) is the command-line interface for executing OQL (Operation Query Language) scenarios. It provides tools to run, validate, and interact with hardware testing scenarios defined in `.oql` files.

## Installation

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Requirements

- Python 3.10+
- `oqlos` runtime (automatically installed as dependency)
- Click 8.0+, Rich 13.0+, HTTPX 0.27+

## Commands

### `run` — Execute a scenario

Run an OQL scenario file against hardware or in simulation mode.

```bash
# Execute mode (default - run on actual hardware)
oqlctl run scenario.oql

# Dry-run mode (validate and simulate without hardware)
oqlctl run scenario.oql --mode dry-run

# Step-by-step manual execution
oqlctl run scenario.oql --step

# Custom firmware server URL
oqlctl run scenario.oql --firmware-url http://localhost:8202
```

### `validate` — Parse and validate

Check an OQL file for syntax errors without executing.

```bash
oqlctl validate scenario.oql
```

### `hardware` — List peripherals

Query the OqlOS API for connected hardware devices.

```bash
# Default localhost
oqlctl hardware

# Custom OqlOS URL
oqlctl hardware --url http://localhost:8200
```

### `scenarios` — List scenarios

List all available scenarios registered with the OqlOS API.

```bash
oqlctl scenarios
oqlctl scenarios --url http://localhost:8200
```

### `shell` — Interactive REPL

Start an interactive OQL shell for testing commands line-by-line.

```bash
oqlctl shell
```

**Shell commands:**
- Type OQL commands directly (e.g., `→ Valve.open NC`, `WAIT 1000`)
- `help` — Show available commands
- `exit` or `quit` — Exit the shell

> `shell` is the easiest place to prototype commands interactively.
> For a single command sent to real hardware, use `cmd` below.

### `cmd` — Execute one command on hardware

Send a single OQL command to the firmware in `execute` mode.

```bash
# Simplest one-liner for hardware execution
oqlctl cmd "SET 'pompa 1' '0'"

# Dry-run / simulation only
oqlctl cmd "SET 'pompa 1' '0'" --mode dry-run

# Custom firmware server URL
oqlctl cmd "SET 'pompa 1' '0'" --firmware-url http://localhost:8202
```

Use `run` with a `.oql` file when you need multiple steps or more complex flow.

## OQL Language Quick Reference

OQL is a declarative DSL for hardware testing scenarios:

```oql
SCENARIO: "Pressure Test"
DEVICE_TYPE: "BA"
DEVICE_MODEL: "PSS 7000"

GOAL: Check Pressure
  1. Open valve:
    → Valve.open NC
    WAIT 2000
    → Sensor.read AI01
    IF [AI01] [>=] [-15 mbar] ELSE ERROR "Pressure too low"
```

**Key constructs:**
- `SCENARIO: "name"` — Scenario metadata
- `DEVICE_TYPE:`, `DEVICE_MODEL:` — Device specification
- `GOAL:` — Define test goals
- `→ Target.method` — Execute hardware actions
- `WAIT ms` — Pause execution
- `IF [sensor] [op] [value] ELSE ERROR "msg"` — Conditional checks
- `SAVE: variable` — Store measurement results

See [OQL Specification](../oqlos/docs/oql-spec.md) for full language reference.

## Project Structure

```
oql/
├── oql/
│   ├── cli.py           # Main CLI entry point
│   ├── adapters/
│   │   └── local.py     # Direct oqlos integration
│   ├── shell/           # Interactive shell implementation
│   │   ├── commands.py  # Shell command registry
│   │   ├── executor.py  # DSL execution engine
│   │   └── runner.py    # Shell/ script runner
│   └── core/            # Core utilities
├── tests/               # Test suite
└── pyproject.toml       # Package configuration
```

## Development

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_cli.py -v
```

## License

Licensed under Apache-2.0.

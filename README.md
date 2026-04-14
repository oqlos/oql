# OQL — Command Line Interface for OqlOS

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Run a scenario
oqlctl run scenario.oql --mode dry-run

# Validate a scenario
oqlctl validate scenario.oql

# List hardware
oqlctl hardware --url http://localhost:8200

# List scenarios
oqlctl scenarios --url http://localhost:8200

# Interactive shell
oqlctl shell
```
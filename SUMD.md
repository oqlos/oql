# OQL — Command Line Interface for OqlOS

OQL CLI — command line interface for OqlOS

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Interfaces](#interfaces)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Release Management (`goal.yaml`)](#release-management-goalyaml)
- [Code Analysis](#code-analysis)
- [Source Map](#source-map)
- [Test Contracts](#test-contracts)
- [Intent](#intent)

## Metadata

- **name**: `oql`
- **version**: `0.1.1`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, pyqual.yaml, goal.yaml, .env.example, src(1 mod), project/(1 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: oql;
  version: 0.1.1;
}

interface[type="cli"] {
  framework: click;
}
interface[type="cli"] page[name="oqlctl"] {

}

workflow[name="install"] {
  trigger: manual;
  step-1: run cmd=pip install -e .[dev];
}

workflow[name="quality"] {
  trigger: manual;
  step-1: run cmd=pyqual run;
}

workflow[name="quality:fix"] {
  trigger: manual;
  step-1: run cmd=pyqual run --fix;
}

workflow[name="quality:report"] {
  trigger: manual;
  step-1: run cmd=pyqual report;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=pytest -q;
}

workflow[name="lint"] {
  trigger: manual;
  step-1: run cmd=ruff check .;
}

workflow[name="fmt"] {
  trigger: manual;
  step-1: run cmd=ruff format .;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=python -m build;
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=rm -rf build/ dist/ *.egg-info;
}

workflow[name="doql:adopt"] {
  trigger: manual;
  step-1: run cmd=if ! command -v {{.DOQL_CMD}} >/dev/null 2>&1; then
  echo "⚠️  doql not installed. Install: pip install doql"
  exit 1
fi;
  step-2: run cmd={{.DOQL_CMD}} adopt {{.PWD}} --output app.doql.css --force;
  step-3: run cmd={{.DOQL_CMD}} export --format less -o {{.DOQL_OUTPUT}};
  step-4: run cmd=echo "✅ Project structure captured in {{.DOQL_OUTPUT}}";
}

workflow[name="doql:validate"] {
  trigger: manual;
  step-1: run cmd=if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
  echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
  exit 1
fi;
  step-2: run cmd={{.DOQL_CMD}} validate;
}

workflow[name="doql:doctor"] {
  trigger: manual;
  step-1: run cmd={{.DOQL_CMD}} doctor;
}

workflow[name="doql:build"] {
  trigger: manual;
  step-1: run cmd=if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
  echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
  exit 1
fi;
  step-2: run cmd=# Regenerate LESS from CSS if CSS exists
if [ -f "app.doql.css" ]; then
  {{.DOQL_CMD}} export --format less -o {{.DOQL_OUTPUT}}
fi;
  step-3: run cmd={{.DOQL_CMD}} build app.doql.css --out build/;
}

workflow[name="help"] {
  trigger: manual;
  step-1: run cmd=task --list;
}

deploy {
  target: docker-compose;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
}
```

### Source Modules

- `oql.cli`

## Interfaces

### CLI Entry Points

- `oqlctl`

### testql Scenarios

#### `testql-scenarios/generated-cli-tests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-cli-tests.testql.toon.yaml
# SCENARIO: CLI Command Tests
# TYPE: cli
# GENERATED: true

CONFIG[2]{key, value}:
  cli_command, python -moql
  timeout_ms, 10000

LOG[3]{message}:
  "Test CLI help command"
  "Test CLI version command"
  "Test CLI main workflow"
```

#### `testql-scenarios/generated-from-pytests.testql.toon.yaml`

```toon markpact:testql path=testql-scenarios/generated-from-pytests.testql.toon.yaml
# SCENARIO: Auto-generated from Python Tests
# TYPE: integration
# GENERATED: true

LOG[4]{message}:
  "Test: TestCli_test_cmd_subcommand_invokes_helper"
  "Test: test_cmd_subcommand_invokes_helper"
  "Test: TestCli_test_cmd_subcommand_invokes_helper"
  "Test: test_cmd_subcommand_invokes_helper"
```

## Workflows

### Taskfile Tasks (`Taskfile.yml`)

```yaml markpact:taskfile path=Taskfile.yml
# Taskfile.yml — oql project runner
# https://taskfile.dev

version: "3"

vars:
  APP_NAME: oql
  DOQL_OUTPUT: app.doql.less
  DOQL_CMD: "{{if eq OS \"windows\"}}doql.exe{{else}}doql{{end}}"

env:
  PYTHONPATH: "{{.PWD}}"

tasks:
  # ─────────────────────────────────────────────────────────────────────────────
  # Development
  # ─────────────────────────────────────────────────────────────────────────────

  install:
    desc: Install Python dependencies (editable)
    cmds:
      - pip install -e .[dev]

  quality:
    desc: Run pyqual quality pipeline
    cmds:
      - pyqual run

  quality:fix:
    desc: Run pyqual with auto-fix
    cmds:
      - pyqual run --fix

  quality:report:
    desc: Generate pyqual quality report
    cmds:
      - pyqual report

  test:
    desc: Run pytest suite
    cmds:
      - pytest -q

  lint:
    desc: Run ruff lint check
    cmds:
      - ruff check .

  fmt:
    desc: Auto-format with ruff
    cmds:
      - ruff format .

  build:
    desc: Build wheel + sdist
    cmds:
      - python -m build

  clean:
    desc: Remove build artefacts
    cmds:
      - rm -rf build/ dist/ *.egg-info

  all:
    desc: Run install, quality check
    cmds:
      - task: install
      - task: quality

  # ─────────────────────────────────────────────────────────────────────────────
  # Doql Integration
  # ─────────────────────────────────────────────────────────────────────────────

  doql:adopt:
    desc: Reverse-engineer oql project structure
    cmds:
      - |
        if ! command -v {{.DOQL_CMD}} >/dev/null 2>&1; then
          echo "⚠️  doql not installed. Install: pip install doql"
          exit 1
        fi
      - "{{.DOQL_CMD}} adopt {{.PWD}} --output app.doql.css --force"
      - "{{.DOQL_CMD}} export --format less -o {{.DOQL_OUTPUT}}"
      - echo "✅ Project structure captured in {{.DOQL_OUTPUT}}"

  doql:validate:
    desc: Validate app.doql.less syntax
    cmds:
      - |
        if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
          echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
          exit 1
        fi
      - "{{.DOQL_CMD}} validate"

  doql:doctor:
    desc: Run doql health checks
    cmds:
      - "{{.DOQL_CMD}} doctor"

  doql:build:
    desc: Generate code from app.doql.less
    cmds:
      - |
        if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
          echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
          exit 1
        fi
      - |
        # Regenerate LESS from CSS if CSS exists
        if [ -f "app.doql.css" ]; then
          {{.DOQL_CMD}} export --format less -o {{.DOQL_OUTPUT}}
        fi
      - "{{.DOQL_CMD}} build app.doql.css --out build/"

  analyze:
    desc: Full doql analysis (adopt + validate + doctor)
    cmds:
      - task: doql:adopt
      - task: doql:validate
      - task: doql:doctor

  # ─────────────────────────────────────────────────────────────────────────────
  # Utility
  # ─────────────────────────────────────────────────────────────────────────────

  help:
    desc: Show available tasks
    cmds:
      - task --list
```

## Quality Pipeline (`pyqual.yaml`)

```yaml markpact:pyqual path=pyqual.yaml
pipeline:
  name: oql-quality

  metrics:
    cc_max: 15
    vallm_pass_min: 65   # current: 68.8%
    # coverage disabled - pytest_cov reports null

  stages:
    - name: analyze
      tool: code2llm-filtered

    - name: validate
      tool: vallm-filtered

    - name: prefact
      tool: prefact
      optional: true
      when: any_stage_fail
      timeout: 900

    - name: fix
      tool: llx-fix
      optional: true
      when: any_stage_fail
      timeout: 1800

    - name: security
      tool: bandit
      optional: true
      timeout: 120

    - name: test
      tool: pytest
      timeout: 600

    - name: push
      tool: git-push
      optional: true
      timeout: 120

  loop:
    max_iterations: 3
    on_fail: report
    ticket_backends:
      - markdown

  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
```

## Configuration

```yaml
project:
  name: oql
  version: 0.1.1
  env: local
```

## Dependencies

### Runtime

```text markpact:deps python
click>=8.0
rich>=13.0
httpx>=0.27
oqlos>=0.1.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
testql>=0.2.0
```

### Development

```text markpact:deps python scope=dev
pytest
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
```

## Deployment

```bash markpact:run
pip install oql

# development install
pip install -e .[dev]
```

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `*(not set)*` | Required: OpenRouter API key (https://openrouter.ai/keys) |
| `LLM_MODEL` | `openrouter/qwen/qwen3-coder-next` | Model (default: openrouter/qwen/qwen3-coder-next) |
| `PFIX_AUTO_APPLY` | `true` | true = apply fixes without asking |
| `PFIX_AUTO_INSTALL_DEPS` | `true` | true = auto pip/uv install |
| `PFIX_AUTO_RESTART` | `false` | true = os.execv restart after fix |
| `PFIX_MAX_RETRIES` | `3` |  |
| `PFIX_DRY_RUN` | `false` |  |
| `PFIX_ENABLED` | `true` |  |
| `PFIX_GIT_COMMIT` | `false` | true = auto-commit fixes |
| `PFIX_GIT_PREFIX` | `pfix:` | commit message prefix |
| `PFIX_CREATE_BACKUPS` | `false` | false = disable .pfix_backups/ directory |

## Release Management (`goal.yaml`)

- **versioning**: `semver`
- **commits**: `conventional` scope=`oql`
- **changelog**: `keep-a-changelog`
- **build strategies**: `python`, `nodejs`, `rust`
- **version files**: `pyproject.toml:version`, `oql/__init__.py:__version__`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# oql | 21f 1379L | python:17,shell:2,css:1,less:1 | 2026-04-18
# stats: 23 func | 10 cls | 21 mod | CC̄=2.9 | critical:1 | cycles:0
# alerts[5]: CC _cmd_list=11; CC run_shell=8; CC shell_cmd=5; CC main=5; CC run=4
# hotspots[5]: run fan=12; hardware fan=9; report fan=8; _cmd_run fan=8; _cmd_list fan=8
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[21]:
  app.doql.css,109
  app.doql.less,111
  oql/__init__.py,4
  oql/adapters/__init__.py,1
  oql/adapters/local.py,21
  oql/adapters/remote.py,35
  oql/cli.py,180
  oql/core/__init__.py,1
  oql/core/event_store.py,16
  oql/shell/__init__.py,16
  oql/shell/api_commands.py,117
  oql/shell/commands.py,139
  oql/shell/executor.py,177
  oql/shell/process_commands.py,69
  oql/shell/protocol_commands.py,72
  oql/shell/runner.py,85
  oql/shell/session_commands.py,103
  oql/shell/ui_commands.py,37
  project.sh,35
  tests/test_cli.py,49
  tree.sh,2
D:
  oql/__init__.py:
  oql/adapters/__init__.py:
  oql/adapters/local.py:
    e: LocalAdapter
    LocalAdapter: __init__(1),execute(1)  # Execute OQL commands directly via oqlos library.
  oql/adapters/remote.py:
    e: RemoteAdapter
    RemoteAdapter: __init__(1),execute(1),list_scenarios(0),list_hardware(0)  # Execute OQL commands via OqlOS REST API.
  oql/cli.py:
    e: main,_build_single_command_scenario,_execute_single_command,run,_generate_report,report,validate,cmd,hardware,scenarios,shell_cmd
    main()
    _build_single_command_scenario(command)
    _execute_single_command(command;firmware_url;mode)
    run(file;step;mode;firmware_url;report;output)
    _generate_report(result;fmt)
    report(data_file;output)
    validate(file)
    cmd(command;mode;firmware_url)
    hardware(url)
    scenarios(url)
    shell_cmd()
  oql/core/__init__.py:
  oql/core/event_store.py:
  oql/shell/__init__.py:
  oql/shell/api_commands.py:
    e: ApiCommandsMixin
    ApiCommandsMixin: cmd_api(1),cmd_create_protocol(1)  # Commands that make HTTP calls to the backend API.
  oql/shell/commands.py:
    e: ShellCommandRegistry,_cmd_exit,_cmd_events,_cmd_clear,_cmd_connect,_cmd_disconnect,_cmd_run,_cmd_scripts,_cmd_list
    ShellCommandRegistry: __init__(0),register(3),get_handler(1)  # Registry for interactive shell commands.
    _cmd_exit(ex;args)
    _cmd_events(ex;args)
    _cmd_clear(ex;args)
    _cmd_connect(ex;args)
    _cmd_disconnect(ex;args)
    _cmd_run(ex;args)
    _cmd_scripts(ex;args)
    _cmd_list(ex;args)
  oql/shell/executor.py:
    e: DslExecutor
    DslExecutor: __init__(1),connect_websocket(1),disconnect_websocket(0),emit_event(2),execute(1),execute_script(1),_parse_target_and_json(1),_generate_id(0)  # Execute DSL commands
  oql/shell/process_commands.py:
    e: ProcessCommandsMixin
    ProcessCommandsMixin: cmd_emit(1),cmd_render(1),cmd_layout(1),cmd_state_save(1),cmd_state_restore(1),cmd_process_start(1),cmd_process_next(1)  # Commands for process flow, components, state, and events.
  oql/shell/protocol_commands.py:
    e: ProtocolCommandsMixin
    ProtocolCommandsMixin: cmd_select_device(1),cmd_select_interval(1),cmd_start_test(1),cmd_step_complete(1),cmd_protocol_created(1),cmd_protocol_finalize(1)  # Commands for test flow and protocol management.
  oql/shell/runner.py:
    e: run_shell,run_script,run_command,main
    run_shell()
    run_script(filename)
    run_command(command)
    main()
  oql/shell/session_commands.py:
    e: SessionCommandsMixin
    SessionCommandsMixin: cmd_record_start(1),cmd_record_stop(1),cmd_wait(1),cmd_log(1),cmd_help(1)  # Commands for recording sessions, waiting, logging, and help.
  oql/shell/ui_commands.py:
    e: UiCommandsMixin
    UiCommandsMixin: cmd_navigate(1),cmd_click(1),cmd_input(1)  # Commands for browser UI interaction.
  tests/test_cli.py:
    e: TestCli
    TestCli: test_help(0),test_version(0),test_single_command_scenario_wrapper(0),test_cmd_subcommand_invokes_helper(1)
```

## Source Map

*Top 1 modules by symbol density — signatures for LLM orientation.*

### `oql.cli` (`oql/cli.py`)

```python
def main()  # CC=1, fan=2
def _build_single_command_scenario(command)  # CC=2, fan=3
def _execute_single_command(command, firmware_url, mode)  # CC=2, fan=3
def run(file, step, mode, firmware_url, report, output)  # CC=4, fan=12
def _generate_report(result, fmt)  # CC=4, fan=5
def report(data_file, output)  # CC=2, fan=8
def validate(file)  # CC=2, fan=7
def cmd(command, mode, firmware_url)  # CC=1, fan=6
def hardware(url)  # CC=2, fan=9
def scenarios(url)  # CC=3, fan=7
def shell_cmd()  # CC=5, fan=7
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (1)

**`Auto-generated from Python Tests`**

## Intent

OQL CLI — command line interface for OqlOS

# OQL — Command Line Interface for OqlOS

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Dependencies](#dependencies)
- [Source Map](#source-map)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `oql`
- **version**: `0.1.1`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(3), app.doql.less, pyqual.yaml, goal.yaml, .env.example, src(1 mod), project/(5 analysis files)

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

  deps:update:
    desc: Upgrade all outdated Python packages in the active / project venv
    cmds:
      - |
        PIP="pip"
        [ -f "{{.PWD}}/.venv/bin/pip" ] && PIP="{{.PWD}}/.venv/bin/pip"
        $PIP install --upgrade pip
        OUTDATED=$($PIP list --outdated --format=columns 2>/dev/null | tail -n +3 | awk '{print $1}')
        if [ -z "$OUTDATED" ]; then
          echo "✅ All packages are up to date."
        else
          echo "📦 Upgrading: $OUTDATED"
          echo "$OUTDATED" | xargs $PIP install --upgrade
          echo "✅ Done."
        fi

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

## Source Map

*Top 1 modules by symbol density — signatures for LLM orientation.*

### `oql.cli` (`oql/cli.py`)

```python
def main()  # CC=1, fan=2
def _build_single_command_scenario(command)  # CC=2, fan=3
def _execute_single_command(command, firmware_url, mode)  # CC=1, fan=3
def run(file, step, mode, firmware_url, report, output)  # CC=3, fan=12
def _generate_report(result, fmt)  # CC=4, fan=5
def report(data_file, output)  # CC=2, fan=8
def validate(file)  # CC=1, fan=7
def cmd(command, mode, firmware_url)  # CC=1, fan=6
def hardware(url)  # CC=2, fan=9
def scenarios(url)  # CC=3, fan=7
def shell_cmd()  # CC=5, fan=7
```

## Call Graph

*6 nodes · 4 edges · 2 modules · CC̄=2.4*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `run_shell` *(in oql.shell.runner)* | 8 | 1 | 10 | **11** |
| `main` *(in oql.shell.runner)* | 5 | 0 | 11 | **11** |
| `cmd` *(in oql.cli)* | 1 | 0 | 7 | **7** |
| `run_command` *(in oql.shell.runner)* | 1 | 1 | 4 | **5** |
| `_execute_single_command` *(in oql.cli)* | 2 | 1 | 3 | **4** |
| `_build_single_command_scenario` *(in oql.cli)* | 2 | 1 | 3 | **4** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/oqlos/oql
# nodes: 6 | edges: 4 | modules: 2
# CC̄=2.4

HUBS[20]:
  oql.shell.runner.run_shell
    CC=8  in:1  out:10  total:11
  oql.shell.runner.main
    CC=5  in:0  out:11  total:11
  oql.cli.cmd
    CC=1  in:0  out:7  total:7
  oql.shell.runner.run_command
    CC=1  in:1  out:4  total:5
  oql.cli._execute_single_command
    CC=2  in:1  out:3  total:4
  oql.cli._build_single_command_scenario
    CC=2  in:1  out:3  total:4

MODULES:
  oql.cli  [3 funcs]
    _build_single_command_scenario  CC=2  out:3
    _execute_single_command  CC=2  out:3
    cmd  CC=1  out:7
  oql.shell.runner  [3 funcs]
    main  CC=5  out:11
    run_command  CC=1  out:4
    run_shell  CC=8  out:10

EDGES:
  oql.cli._execute_single_command → oql.cli._build_single_command_scenario
  oql.cli.cmd → oql.cli._execute_single_command
  oql.shell.runner.main → oql.shell.runner.run_shell
  oql.shell.runner.main → oql.shell.runner.run_command
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (1)

**`CLI Command Tests`**

### Integration (2)

**`Cross-Project Integration Tests`**

**`Auto-generated from Python Tests`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/oqlos/oql
# nodes: 6 | edges: 4 | modules: 2
# CC̄=2.4

HUBS[20]:
  oql.shell.runner.run_shell
    CC=8  in:1  out:10  total:11
  oql.shell.runner.main
    CC=5  in:0  out:11  total:11
  oql.cli.cmd
    CC=1  in:0  out:7  total:7
  oql.shell.runner.run_command
    CC=1  in:1  out:4  total:5
  oql.cli._execute_single_command
    CC=2  in:1  out:3  total:4
  oql.cli._build_single_command_scenario
    CC=2  in:1  out:3  total:4

MODULES:
  oql.cli  [3 funcs]
    _build_single_command_scenario  CC=2  out:3
    _execute_single_command  CC=2  out:3
    cmd  CC=1  out:7
  oql.shell.runner  [3 funcs]
    main  CC=5  out:11
    run_command  CC=1  out:4
    run_shell  CC=8  out:10

EDGES:
  oql.cli._execute_single_command → oql.cli._build_single_command_scenario
  oql.cli.cmd → oql.cli._execute_single_command
  oql.shell.runner.main → oql.shell.runner.run_shell
  oql.shell.runner.main → oql.shell.runner.run_command
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 18f 1093L | python:16,shell:2 | 2026-04-19
# CC̄=2.4 | critical:0/63 | dups:0 | cycles:0

HEALTH[0]: ok

REFACTOR[0]: none needed

PIPELINES[54]:
  [1] Src [cmd_select_device]: cmd_select_device
      PURITY: 100% pure
  [2] Src [cmd_select_interval]: cmd_select_interval
      PURITY: 100% pure
  [3] Src [cmd_start_test]: cmd_start_test
      PURITY: 100% pure
  [4] Src [cmd_step_complete]: cmd_step_complete
      PURITY: 100% pure
  [5] Src [cmd_protocol_created]: cmd_protocol_created
      PURITY: 100% pure

LAYERS:
  oql/                            CC̄=2.4    ←in:0  →out:0
  │ cli                        179L  0C   11m  CC=5      ←0
  │ executor                   176L  1C    8m  CC=9      ←0
  │ commands                   138L  1C   11m  CC=11     ←0
  │ api_commands               116L  1C    2m  CC=11     ←0
  │ session_commands           102L  1C    5m  CC=2      ←0
  │ runner                      84L  0C    4m  CC=8      ←0
  │ protocol_commands           71L  1C    6m  CC=3      ←0
  │ process_commands            68L  1C    7m  CC=3      ←0
  │ ui_commands                 36L  1C    3m  CC=1      ←0
  │ remote                      34L  1C    4m  CC=1      ←0
  │ local                       20L  1C    2m  CC=1      ←0
  │ event_store                 15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.0    ←in:0  →out:0
  │ project.sh                  35L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     oql/adapters/__init__.py                  0L
     oql/core/__init__.py                      0L

COUPLING: no cross-package imports detected

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 63 func | 11f | 2026-04-19

NEXT[0]: no refactoring needed

RISKS[0]: none

METRICS-TARGET:
  CC̄:          2.4 → ≤1.7
  max-CC:      11 → ≤5
  god-modules: 0 → 0
  high-CC(≥15): 0 → ≤0
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=2.4 → now CC̄=2.4
```

### Validation (`project/validation.toon.yaml`)

```toon markpact:analysis path=project/validation.toon.yaml
# vallm batch | 34f | 23✓ 0⚠ 0✗ | 2026-04-18

SUMMARY:
  scanned: 34  passed: 23 (67.6%)  warnings: 0  errors: 0  unsupported: 11

UNSUPPORTED[3]{bucket,count}:
  *.md,5
  *.yml,2
  other,4
```

## Intent

OQL CLI — command line interface for OqlOS

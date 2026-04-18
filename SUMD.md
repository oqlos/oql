# OQL — Command Line Interface for OqlOS

OQL CLI — command line interface for OqlOS

## Metadata

- **name**: `oql`
- **version**: `0.1.1`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, testql(2), app.doql.less, app.doql.css, pyqual.yaml, goal.yaml, .env.example, src(1 mod)

## Intent

OQL CLI — command line interface for OqlOS

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`, `app.doql.css`)

```less
// LESS format — define @variables here as needed

app {
  name: "oql";
  version: "0.1.1";
}

interface[type="cli"] {
  framework: click;
}
interface[type="cli"] page[name="oqlctl"] {

}

workflow[name="install"] {
  trigger: """""""manual""""""";
}

workflow[name="test"] {
  trigger: """""""manual""""""";
}

workflow[name="lint"] {
  trigger: """""""manual""""""";
}

workflow[name="fmt"] {
  trigger: """""""manual""""""";
}

workflow[name="build"] {
  trigger: """""""manual""""""";
}

workflow[name="clean"] {
  trigger: """""""manual""""""";
}

workflow[name="doql:adopt"] {
  trigger: """""""manual""""""";
}

workflow[name="doql:validate"] {
  trigger: """""""manual""""""";
}

workflow[name="doql:doctor"] {
  trigger: """""""manual""""""";
}

workflow[name="doql:build"] {
  trigger: """""""manual""""""";
}

workflow[name="help"] {
  trigger: """""""manual""""""";
}

deploy {
  target: docker-compose;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: """"""".env""""""";
}
```

```css
app {
  name: "oql";
  version: "0.1.1";
}

interface[type="cli"] {
  framework: click;
}
interface[type="cli"] page[name="oqlctl"] {

}

workflow[name="install"] {
  trigger: "manual";
  step-1: run cmd=pip install -e .[dev];
}

workflow[name="test"] {
  trigger: "manual";
  step-1: run cmd=pytest -q;
}

workflow[name="lint"] {
  trigger: "manual";
  step-1: run cmd=ruff check .;
}

workflow[name="fmt"] {
  trigger: "manual";
  step-1: run cmd=ruff format .;
}

workflow[name="build"] {
  trigger: "manual";
  step-1: run cmd=python -m build;
}

workflow[name="clean"] {
  trigger: "manual";
  step-1: run cmd=rm -rf build/ dist/ *.egg-info;
}

workflow[name="doql:adopt"] {
  trigger: "manual";
  step-1: run cmd=if ! command -v {{.DOQL_CMD}} >/dev/null 2>&1; then
  echo "⚠️  doql not installed. Install: pip install doql"
  exit 1
fi;
  step-2: run cmd={{.DOQL_CMD}} adopt {{.PWD}} --output app.doql.css --force;
  step-3: run cmd={{.DOQL_CMD}} export --format less -o {{.DOQL_OUTPUT}};
  step-4: run cmd=echo "✅ Project structure captured in {{.DOQL_OUTPUT}}";
}

workflow[name="doql:validate"] {
  trigger: "manual";
  step-1: run cmd=if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
  echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
  exit 1
fi;
  step-2: run cmd={{.DOQL_CMD}} validate;
}

workflow[name="doql:doctor"] {
  trigger: "manual";
  step-1: run cmd={{.DOQL_CMD}} doctor;
}

workflow[name="doql:build"] {
  trigger: "manual";
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
  trigger: "manual";
  step-1: run cmd=task --list;
}

deploy {
  target: docker-compose;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: ".env";
}
```

### Source Modules

- `oql.cli`

## Interfaces

### CLI Entry Points

- `oqlctl`

### testql Scenarios

#### `testql-scenarios/generated-cli-tests.testql.toon.yaml`

```toon
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

```toon
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

```yaml
tasks:
  install:
    desc: "Install Python dependencies (editable)"
    cmds:
      - pip install -e .[dev]
  quality:
    desc: "Run pyqual quality pipeline"
    cmds:
      - pyqual run
  quality:fix:
    desc: "Run pyqual with auto-fix"
    cmds:
      - pyqual run --fix
  quality:report:
    desc: "Generate pyqual quality report"
    cmds:
      - pyqual report
  test:
    desc: "Run pytest suite"
    cmds:
      - pytest -q
  lint:
    desc: "Run ruff lint check"
    cmds:
      - ruff check .
  fmt:
    desc: "Auto-format with ruff"
    cmds:
      - ruff format .
  build:
    desc: "Build wheel + sdist"
    cmds:
      - python -m build
  clean:
    desc: "Remove build artefacts"
    cmds:
      - rm -rf build/ dist/ *.egg-info
  all:
    desc: "Run install, quality check"
  doql:adopt:
    desc: "Reverse-engineer oql project structure"
    cmds:
      - if ! command -v {{.DOQL_CMD}} >/dev/null 2>&1; then
  echo "⚠️  doql not installed. Install: pip install doql"
  exit 1
fi
  doql:validate:
    desc: "Validate app.doql.less syntax"
    cmds:
      - if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
  echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
  exit 1
fi
  doql:doctor:
    desc: "Run doql health checks"
    cmds:
      - {{.DOQL_CMD}} doctor
  doql:build:
    desc: "Generate code from app.doql.less"
    cmds:
      - if [ ! -f "{{.DOQL_OUTPUT}}" ]; then
  echo "❌ {{.DOQL_OUTPUT}} not found. Run: task doql:adopt"
  exit 1
fi
  analyze:
    desc: "Full doql analysis (adopt + validate + doctor)"
  help:
    desc: "Show available tasks"
    cmds:
      - task --list
```

## Quality Pipeline (`pyqual.yaml`)

```yaml
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

- `click>=8.0`
- `rich>=13.0`
- `httpx>=0.27`
- `oqlos>=0.1.0`
- `goal>=2.1.0`
- `costs>=0.1.20`
- `pfix>=0.1.60`
- `testql>=0.2.0`

### Development

- `pytest`
- `goal>=2.1.0`
- `costs>=0.1.20`
- `pfix>=0.1.60`

## Deployment

```bash
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

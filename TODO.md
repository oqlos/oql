# OQL TODO

## P0 — Critical

- [ ] `parse_oql` CC=34 in `oql/parser.py` — split into sub-parsers per construct type
- [ ] pytest coverage is not collected (add `pytest-cov` + `.coveragerc`)

## P1 — Quality

- [ ] `shell/executor.py` — extract command dispatch table (currently chained if/elif)
- [ ] `cli.py` god function for `run` command — extract `_run_scenario`, `_run_step_mode`
- [ ] Integration tests require live OqlOS server — add mock adapter for CI

## P2 — Features / Backlog

- [ ] `oqlctl validate` — add JSON schema output option (`--format json`)
- [ ] `oqlctl scenarios` — add filtering by `DEVICE_TYPE`
- [ ] `oqlctl shell` — history persistence between sessions (readline)
- [ ] `oqlctl cmd` — batch mode: read commands from stdin

## Tests

- [ ] Run `testql run testql-scenarios/generated-cli-tests.testql.toon.yaml` and fix failures
- [ ] Run `testql run testql-scenarios/generated-from-pytests.testql.toon.yaml`
- [ ] Run `testql run testql-scenarios/cross-project-integration.testql.toon.yaml`

## ✅ Done

- [x] Initial CLI scaffold: run, validate, hardware, scenarios, shell, cmd
- [x] OQL language quick reference in README
- [x] testql-scenarios generated (3 files)
- [x] CHANGELOG updated with structured entries

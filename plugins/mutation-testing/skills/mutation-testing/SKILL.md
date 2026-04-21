---
name: mutation-testing
version: "1.0.0"
description: >
  Validates test quality beyond coverage: uses Claude to generate intelligent mutations for source
  code, runs them via the project's native test runner (pytest, jest, vitest, mocha, go test),
  prints a structured summary, extracts survived mutants, generates mutation-todos.md with per-mutant
  rationale, persists every run to a per-project SQLite ledger and JSONL trace under
  ~/logbooks/mutation-testing/, and warns when the mutation score falls below 70%.
  Requires ANTHROPIC_API_KEY.
  Invoke for: "run mutation tests", "check mutation score", "mutation testing", "are our tests
  actually testing anything?", "which tests are weak?", "test quality check".
  Do not invoke for plain unit test runs, coverage reports, linting, or type checking.
---

# Mutation Testing

Tests pass ≠ tests are useful. This skill uses Claude to generate meaningful mutations for source
code, then runs the project's existing test suite against each one. A surviving mutant is a gap —
a real bug the suite would miss.

## What this skill does

1. **Discovers source files** — auto-detects from project structure, or uses `--sources` globs
2. **Detects test runner** — infers from project config files (pytest, jest, vitest, mocha, go test)
3. **Checks baseline** — verifies the test suite passes before mutating anything
4. **Generates mutations via Claude** — intelligent, context-aware mutations per file
5. **Applies each mutation** — writes the mutated file to disk, one at a time
6. **Runs the test suite** — records `Killed` (tests failed) vs. `Survived` (tests passed)
7. **Restores each file** — always restores the original before the next mutation
8. **Generates mutation-todos.md** — table of survivors with rationale for each gap
9. **Persists to logbook** — SQLite + JSONL under `~/logbooks/mutation-testing/`
10. **Warns if score < 70%** — exits with code 2

---

## How to run

```bash
# Auto-detect sources and test runner
python plugins/mutation-testing/skills/mutation-testing/scripts/mutation_testing.py

# Specify source globs explicitly
python ... --sources "src/**/*.py" "lib/**/*.py"

# Custom runner, threshold, and timeout
python ... --runner pytest --threshold 80 --timeout 120

# Limit mutations per file (faster runs)
python ... --max-per-file 5

# Use a faster/cheaper model
python ... --model claude-sonnet-4-6

# Skip logbook writes
python ... --no-logbook
```

## CLI flags

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--sources GLOB [GLOB …]` | auto | Glob patterns for source files to mutate |
| `--runner` | auto | `pytest` \| `jest` \| `vitest` \| `mocha` \| `go_test` \| `npm_test` |
| `--threshold` | `70` | Minimum acceptable mutation score |
| `--timeout` | `60` | Seconds allowed per test run |
| `--max-per-file` | `10` | Max mutations Claude generates per source file |
| `--model` | `claude-opus-4-7` | Claude model for mutation generation |
| `--mutations-file PATH` | off | Load pre-generated mutations from a JSON file — skips Claude API call entirely. Useful for deterministic runs, offline use, or when the caller (e.g. Claude Code) generates mutations itself. `ANTHROPIC_API_KEY` is not required when this flag is set. |
| `--skip-baseline` | off | Skip the pre-mutation baseline pass check |
| `--no-logbook` | off | Skip SQLite/JSONL logbook writes |

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | Success — score ≥ threshold |
| `1` | Setup, generation, or baseline failure |
| `2` | Score below threshold |

---

## Prerequisites

- `ANTHROPIC_API_KEY` environment variable set
- Python 3.10+ (uses `match`/`case` and `str.removesuffix`)
- `anthropic` SDK installed: `pip install anthropic`
- A working test suite (tests must pass before running mutation tests)
- At least one source file (auto-detected or via `--sources`)

---

## Auto-detection

### Source files

Searches in order: `src/`, `lib/`, project root. Finds `.py` first, then `.ts`, then `.js`.
Test files are excluded (`test_*.py`, `*_test.py`, `*.spec.*`, `*.test.*`, paths containing
`test/` or `tests/`). Capped at 20 files per run.

> **Caveat:** Discovery picks the first language bucket it finds. In polyglot repos (e.g. a Python
> project with TypeScript tooling) it may pick the wrong language. Use `--sources` explicitly in
> those cases.

### Test runner

Detected from project config files in the working directory:

| Signal | Runner |
| ------ | ------ |
| `pytest.ini`, `conftest.py`, `[tool.pytest]` in `pyproject.toml` | `pytest` |
| `jest.config.*` or `"jest"` in `package.json` devDependencies | `jest` |
| `"vitest"` in `package.json` devDependencies | `vitest` |
| `"mocha"` in `package.json` devDependencies | `mocha` |
| Any `*.go` file present | `go test ./...` |
| `"test"` script in `package.json` | `npm test` |

> **Caveat:** Detection can mislead in mixed repos. A repo with both `jest` and `vitest` in
> devDependencies will resolve to whichever appears first. Use `--runner` explicitly when
> auto-detection is unreliable.

---

## Mutant statuses

| Status | Meaning |
| ------ | ------- |
| `Killed` | Tests detected the bug — good |
| `Survived` | No test caught the bug — **test gap** |
| `Error` | Test runner failed or errored |
| `Skipped` | Original line didn't match Claude's expected text |

## Score formula

```
score = Killed / (Killed + Survived + Errors) × 100
```

Skipped mutants are excluded from the denominator.

| Score | Assessment |
| ----- | ---------- |
| ≥ 90% | Strong test suite |
| 70–90% | Acceptable — review survivors |
| < 70% | Weak — prioritise mutation-todos.md |

---

## Output artifacts

| Artifact | Location | Description |
| -------- | -------- | ----------- |
| `mutation-todos.md` | repo root | Survivors table with rationale |
| SQLite ledger | `~/logbooks/mutation-testing/{slug}.sqlite` | Run history + survivors |
| JSONL trace | `~/logbooks/mutation-testing/{slug}.jsonl` | Append-only run log |

---

## Logbook spec

Full schema, query examples, and export setup: `mutation-runs.logbook.md`.

## Claude API reference

Mutation generation design, model tradeoffs, prompt caching: `references/ai-mutation.md`.

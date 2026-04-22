---
name: mutation-testing
version: "2.0.0"
description: >
  Validates test quality beyond coverage: uses Claude subagents to generate intelligent mutations
  for source code, runs them via the project's native test runner (pytest, jest, vitest, mocha,
  go test), prints a structured summary, generates mutation-todos.md with per-mutant rationale,
  persists every run to a per-project SQLite ledger and JSONL trace under
  ~/logbooks/mutation-testing/, and warns when the mutation score falls below 70%.
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
4. **Generates mutations via subagents** — dispatches one Task per source file in parallel; each
   subagent reads the file and returns a JSON array of mutations; results are merged into a single
   `mutations.json` file
5. **Applies each mutation** — writes the mutated file to disk, one at a time
6. **Runs the test suite** — records `Killed` (tests failed) vs. `Survived` (tests passed)
7. **Restores each file** — always restores the original before the next mutation
8. **Generates mutation-todos.md** — table of survivors with rationale for each gap
9. **Persists to logbook** — SQLite + JSONL under `~/logbooks/mutation-testing/`
10. **Warns if score < 70%** — exits with code 2

---

## How to invoke this skill

This skill follows a two-phase protocol: **generate** then **run**.

### Phase 1 — Generate mutations (caller's responsibility)

For each source file to mutate, dispatch a subagent with this prompt template:

> You are a mutation testing expert. Generate up to `{max_per_file}` meaningful mutations for the
> following source file that will expose gaps in the test suite.
>
> Already-known open gaps (do NOT regenerate these — find new ones):
> `{known_gaps_for_file}`
>
> File: `{rel_path}`
> ```
> {line_numbered_source}
> ```
>
> Return a JSON array. Each element must be an object with these keys:
> - `id` (string) — unique ID, e.g. `"m1"`
> - `mutatorName` (string) — operator name, e.g. `"FlipGreaterThan"`
> - `line` (integer) — 1-based line number
> - `original_line` (string) — complete original line, leading whitespace preserved
> - `mutated_line` (string) — complete mutated line, leading whitespace preserved
> - `replacement` (string) — short change description, e.g. `"> → >="`
> - `rationale` (string) — why this exposes a test gap
> - `file` (string) — relative path of the file
>
> Target: conditional flips (`>` → `>=`), boolean negation, arithmetic swaps, return value changes,
> string literal blanking, boundary shifts, argument removal/swap.
> Skip: comments, imports, type annotations, docstrings, blank lines, logging.

Collect all subagent outputs, merge into a single JSON array, and save to a temp file
(e.g. `/tmp/mutations.json`).

**Tips:**
- Dispatch subagents in parallel (one per file) for speed
- Pass `--model claude-sonnet-4-6` as a logbook hint if using a cheaper model
- Query prior open gaps first (from the logbook SQLite) and pass them per-file so subagents
  generate novel mutations rather than re-discovering known gaps

### Phase 2 — Run the script

```bash
python plugins/mutation-testing/skills/mutation-testing/scripts/mutation_testing.py \
  --mutations-file /tmp/mutations.json
```

With options:

```bash
# Specify source globs explicitly (for display / auto-detection context)
python ... --mutations-file /tmp/mutations.json --sources "src/**/*.py" "lib/**/*.py"

# Custom runner, threshold, and timeout
python ... --mutations-file /tmp/mutations.json --runner pytest --threshold 80 --timeout 120

# Record which model was used for generation (metadata only)
python ... --mutations-file /tmp/mutations.json --model claude-sonnet-4-6

# Skip logbook writes
python ... --mutations-file /tmp/mutations.json --no-logbook
```

## CLI flags

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--mutations-file PATH` | **required** | JSON file of pre-generated mutations |
| `--sources GLOB [GLOB …]` | auto | Glob patterns for source files (used for display and auto-detection) |
| `--runner` | auto | `pytest` \| `jest` \| `vitest` \| `mocha` \| `go_test` \| `npm_test` |
| `--threshold` | `70` | Minimum acceptable mutation score |
| `--timeout` | `60` | Seconds allowed per test run |
| `--model` | `claude-opus-4-7` | Claude model used for generation — recorded in logbook as metadata |
| `--skip-baseline` | off | Skip the pre-mutation baseline pass check |
| `--no-logbook` | off | Skip SQLite/JSONL logbook writes |

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | Success — score ≥ threshold |
| `1` | Setup, load, or baseline failure; or all mutations skipped |
| `2` | Score below threshold |

---

## Prerequisites

- Python 3.10+ (uses `match`/`case` and `str.removesuffix`)
- A working test suite (tests must pass before running mutation tests)
- At least one source file (auto-detected or via `--sources`)
- No SDK or API key required — mutation generation is done by the calling Claude agent

---

## Auto-detection

### Source files

Searches in order: `src/`, `lib/`, project root. Finds `.py` first, then `.ts`, then `.js`.
Test files are excluded (`test_*.py`, `*_test.py`, `*.spec.*`, `*.test.*`, paths containing
`test/` or `tests/`). Directories `.venv`, `.git`, `dist`, `build`, `__pycache__`, and similar
are excluded. Capped at 20 files per run.

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
| `Skipped` | Original line didn't match the expected text |

## Score formula

```
score = Killed / (Killed + Survived + Errors) × 100
```

Skipped mutants are excluded from the denominator. If all mutants are skipped, the script exits 1
(setup issue, not a score failure).

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

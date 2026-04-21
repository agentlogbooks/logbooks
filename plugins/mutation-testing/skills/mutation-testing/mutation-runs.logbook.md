---
schema_version: 2
scope: solo-cross-machine
bindings:
  # GOVERNANCE: This file is a shared repo artifact — permanently read-only once committed.
  # Never edit address_pattern or binding fields here. Store credentials and active status
  # in a local-only override (e.g. ~/logbooks/mutation-testing/bindings.local.yaml).
  # Agents must never write back to this file.

  # Per-project SQLite ledger — {slug} resolved to project name at runtime
  - driver: sqlite
    label: ledger
    address_pattern: ~/logbooks/mutation-testing/{slug}.sqlite
    note: >
      contains `runs`, `mutant_results`, `mutants`, `gap_ledger` tables;
      {slug} = sanitized git remote name or cwd name

  # Per-project JSONL trace — append-only
  - driver: jsonl
    label: run-log
    address_pattern: ~/logbooks/mutation-testing/{slug}.jsonl
    note: record_type one of `run` | `mutant_result` | `gap_update`

  # Optional human-facing export
  - driver: google_sheets
    label: mutation-export
    address_pattern: gsheets://SPREADSHEET_ID_PLACEHOLDER/mutation_runs?gws_account=GWS_ACCOUNT
    status: pending-auth
    mode: export-only
---

# Mutation Testing Logbook v2

Per-project structured store for AI-based mutation test runs. Three concerns are kept separate:

## When this pays off

The logbook earns its weight when you can answer questions across runs, not just within one:

- **Did the mutation score improve after we added tests?** — score trend in `runs`
- **Which survivors keep coming back?** — `times_survived` in `mutants`
- **Which files are chronic weak spots?** — open gap counts by file in `gap_ledger`
- **Did this refactor make test quality worse?** — score regression query across runs
- **What should we fix next?** — open gaps ordered by `times_survived` (repeated evidence, not one-run noise)

The history layer has almost no leverage on a first run. It starts paying off on the second or
third run, and compounds from there.

It is especially worth wiring up if:
- You run mutation testing on the same repo regularly
- A human reviews survivors over time
- Another agent uses prior results to decide what to test next
- You need durable gap memory across sessions instead of rediscovering the same gaps each run

If you are running mutation testing once as a one-shot audit, skip the logbook (`--no-logbook`).

| Layer | Table | Mutable? | Purpose |
|-------|-------|----------|---------|
| History | `runs` | No | One row per execution, score + counters |
| Outcomes | `mutant_results` | No | Every mutant result from every run |
| Identity | `mutants` | Append + update counters | Canonical mutant, aggregated across runs |
| State | `gap_ledger` | Yes | Current open/fixed/acknowledged gaps |

The `gap_ledger` is the key addition over v1: it is a **patchable present-tense view** of which
gaps are still open, independent of run history. Closing a gap (test added, code fixed) is a first-
class operation, not just an absence of the mutant in the next run.

## Physical stores

- **SQLite** — `~/logbooks/mutation-testing/{slug}.sqlite`
- **JSONL** — `~/logbooks/mutation-testing/{slug}.jsonl` — append-only trace

## Design principles

- `runs` and `mutant_results` are **append-only** — never update prior rows.
- `mutants` rows are **upserted** — counters increment on each run.
- `gap_ledger` rows are **patched** — status transitions as gaps open and close.
- `mutant_key` is a stable 16-char hex digest of `file:line:mutator:original_line` — survives
  re-runs but changes if the source line is edited (correct: it's a new mutation location).
- Skipped mutants are excluded from score and not written to `mutant_results`.

---

## Tables

### runs

One row per mutation test run. Append-only.

| Column | Type | Notes |
| ------ | ---- | ----- |
| run_id | text PK | `{YYYYMMDD-HHmmss}-{slug}` |
| project | text NOT NULL | Project slug |
| ran_at | text NOT NULL | ISO 8601 UTC datetime |
| score | real NOT NULL | Mutation score 0–100 |
| killed | integer NOT NULL | Mutants detected by tests |
| survived | integer NOT NULL | Mutants not caught — test gaps |
| errors | integer NOT NULL | Mutants that errored |
| skipped | integer NOT NULL | Mutants skipped (line mismatch) — excluded from score |
| total | integer NOT NULL | `killed + survived + errors` |
| threshold | real NOT NULL | Score threshold used for this run |
| passed | integer NOT NULL | 1 if score ≥ threshold, 0 otherwise |
| model | text | Claude model used for mutation generation |

### mutant_results

One row per mutant per run. Append-only. Replaces v1 `survivors` (now covers all outcomes).

| Column | Type | Notes |
| ------ | ---- | ----- |
| run_id | text NOT NULL FK | References `runs.run_id` |
| mutant_key | text NOT NULL FK | References `mutants.mutant_key` |
| status | text NOT NULL | `Killed` \| `Survived` \| `Error` |
| PRIMARY KEY | | `(run_id, mutant_key)` |

### mutants

One row per unique mutant identity. Upserted on each run (counters increment).

| Column | Type | Notes |
| ------ | ---- | ----- |
| mutant_key | text PK | `sha256(file:line:mutator:original_line)[:16]` |
| project | text NOT NULL | |
| file | text NOT NULL | Source file path (relative to repo root) |
| line | integer | 1-based line number |
| col | integer | 1-based column (nullable) |
| mutator | text NOT NULL | Operator name, e.g. `FlipGreaterThan` |
| replacement | text | Short change description, e.g. `> → >=` |
| original_line | text | Complete original source line |
| mutated_line | text | Complete mutated line |
| rationale | text | Why this exposes a test gap |
| first_seen | text NOT NULL | run_id of first appearance |
| last_seen | text NOT NULL | run_id of most recent appearance |
| times_survived | integer NOT NULL | Cumulative survived count |
| times_killed | integer NOT NULL | Cumulative killed count |
| last_status | text NOT NULL | Most recent status for this mutant |

### gap_ledger

One row per surviving mutant gap — the **patchable present-tense view**.

| Column | Type | Notes |
| ------ | ---- | ----- |
| mutant_key | text PK FK | References `mutants.mutant_key` |
| status | text NOT NULL | `open` \| `acknowledged` \| `fixed` \| `wont_fix` |
| opened_at | text NOT NULL | ISO 8601 UTC — when first marked open |
| updated_at | text NOT NULL | ISO 8601 UTC — last status change |
| note | text | Human or agent annotation |

**Status transitions:**

```
             run survives          run kills (and status=open)
[absent] ──────────────► [open] ──────────────────────────────► [fixed]
                           │  ▲                                     │
               human/agent │  │ human/agent reopen                 │
                           ▼  │                                     │
                    [acknowledged]                            [wont_fix]
                    [wont_fix]
```

- On each run: surviving mutants → gap `open` (unless already `acknowledged` or `wont_fix`).
- On each run: killed mutants with gap status `open` → gap `fixed`.
- `acknowledged` / `wont_fix` are human/agent annotations; runs do not overwrite them.

---

## JSONL record types

| record_type | Written when | Key fields |
| ----------- | ------------ | ---------- |
| `run` | After stats are computed | run_id, project, ran_at, score, killed, survived, errors, skipped, total, threshold, passed, model |
| `mutant_result` | Once per non-skipped mutant | run_id, mutant_key, project, file, line, mutator, replacement, status |
| `gap_update` | When gap_ledger changes | mutant_key, project, old_status, new_status, note, updated_at |

---

## SQLite initialization

```sql
CREATE TABLE IF NOT EXISTS runs (
    run_id    TEXT PRIMARY KEY,
    project   TEXT NOT NULL,
    ran_at    TEXT NOT NULL,
    score     REAL NOT NULL,
    killed    INTEGER NOT NULL,
    survived  INTEGER NOT NULL,
    errors    INTEGER NOT NULL,
    skipped   INTEGER NOT NULL,
    total     INTEGER NOT NULL,
    threshold REAL NOT NULL,
    passed    INTEGER NOT NULL,
    model     TEXT
);

CREATE TABLE IF NOT EXISTS mutants (
    mutant_key     TEXT PRIMARY KEY,
    project        TEXT NOT NULL,
    file           TEXT NOT NULL,
    line           INTEGER,
    col            INTEGER,
    mutator        TEXT NOT NULL,
    replacement    TEXT,
    original_line  TEXT,
    mutated_line   TEXT,
    rationale      TEXT,
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    times_survived INTEGER NOT NULL DEFAULT 0,
    times_killed   INTEGER NOT NULL DEFAULT 0,
    last_status    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mutant_results (
    run_id      TEXT NOT NULL REFERENCES runs(run_id),
    mutant_key  TEXT NOT NULL REFERENCES mutants(mutant_key),
    status      TEXT NOT NULL,
    PRIMARY KEY (run_id, mutant_key)
);

CREATE TABLE IF NOT EXISTS gap_ledger (
    mutant_key TEXT PRIMARY KEY REFERENCES mutants(mutant_key),
    status     TEXT NOT NULL CHECK(status IN ('open','acknowledged','fixed','wont_fix')),
    opened_at  TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    note       TEXT
);

CREATE INDEX IF NOT EXISTS idx_mutant_results_run    ON mutant_results(run_id);
CREATE INDEX IF NOT EXISTS idx_mutant_results_mutant ON mutant_results(mutant_key);
CREATE INDEX IF NOT EXISTS idx_mutants_file          ON mutants(file);
CREATE INDEX IF NOT EXISTS idx_gap_ledger_status     ON gap_ledger(status);
```

---

## Queries

### Score trend across runs

```sql
SELECT run_id, ran_at, score, survived, passed, model
FROM runs
ORDER BY ran_at DESC
LIMIT 20;
```

### Current open gaps (the actionable list)

```sql
SELECT m.file, m.line, m.mutator, m.replacement, m.rationale,
       m.times_survived, g.opened_at, g.note
FROM gap_ledger g
JOIN mutants m USING (mutant_key)
WHERE g.status = 'open'
ORDER BY m.times_survived DESC, m.file, m.line;
```

### Persistent gaps — survived 3+ runs without being acknowledged

```sql
SELECT m.file, m.line, m.mutator, m.replacement, m.times_survived,
       m.first_seen, m.last_seen
FROM mutants m
JOIN gap_ledger g USING (mutant_key)
WHERE g.status = 'open' AND m.times_survived >= 3
ORDER BY m.times_survived DESC;
```

### Gaps fixed since last run (mutants killed this run that had an open gap)

```sql
SELECT m.file, m.line, m.mutator, m.replacement, g.updated_at
FROM gap_ledger g
JOIN mutants m USING (mutant_key)
WHERE g.status = 'fixed'
ORDER BY g.updated_at DESC
LIMIT 20;
```

### Score regression — runs where score dropped vs previous

```sql
SELECT a.run_id, a.ran_at, a.score,
       LAG(a.score) OVER (ORDER BY a.ran_at) AS prev_score,
       a.score - LAG(a.score) OVER (ORDER BY a.ran_at) AS delta
FROM runs a
ORDER BY a.ran_at DESC;
```

### Hotspot files — open gaps by file

```sql
SELECT m.file, COUNT(*) AS open_gaps
FROM gap_ledger g
JOIN mutants m USING (mutant_key)
WHERE g.status = 'open'
GROUP BY m.file
ORDER BY open_gaps DESC;
```

### Full history for one mutant

```sql
SELECT r.run_id, r.ran_at, mr.status
FROM mutant_results mr
JOIN runs r USING (run_id)
WHERE mr.mutant_key = '<key>'
ORDER BY r.ran_at;
```

---

## Gap ledger patch operations

These are run by humans or agents to annotate gaps — not by the mutation testing runner itself.

```sql
-- Acknowledge a gap (known issue, not going to fix now)
UPDATE gap_ledger
SET status = 'acknowledged', note = 'tracked in PROJ-123', updated_at = datetime('now')
WHERE mutant_key = '<key>';

-- Mark won't fix
UPDATE gap_ledger
SET status = 'wont_fix', note = 'boundary intentionally not tested', updated_at = datetime('now')
WHERE mutant_key = '<key>';

-- Reopen an acknowledged gap (e.g. the underlying code changed)
UPDATE gap_ledger
SET status = 'open', note = 'reopened: code refactored', updated_at = datetime('now')
WHERE mutant_key = '<key>';
```

---

## JSONL: recent gap updates

```bash
grep '"record_type":"gap_update"' ~/logbooks/mutation-testing/myproject.jsonl \
  | jq -s 'sort_by(.updated_at) | reverse | .[:10][] | {mutant_key, old_status, new_status, note, updated_at}'
```

---

## Migration from v1

```sql
-- Create new tables (see initialization above)

-- Backfill mutants from v1 survivors
INSERT OR IGNORE INTO mutants
    (mutant_key, project, file, line, col, mutator, replacement,
     original_line, mutated_line, rationale,
     first_seen, last_seen, times_survived, times_killed, last_status)
SELECT
    lower(hex(randomblob(8))) AS mutant_key,  -- approximate; re-run to get real keys
    project, file, line, col, mutator, replacement,
    original_line, mutated_line, rationale,
    min(run_id), max(run_id),
    COUNT(*), 0, 'Survived'
FROM survivors
GROUP BY file, line, mutator, original_line;

-- Backfill gap_ledger from current surviving mutants
INSERT OR IGNORE INTO gap_ledger (mutant_key, status, opened_at, updated_at)
SELECT mutant_key, 'open', first_seen, last_seen
FROM mutants;
```

---

## Governance

- **Append layers** (`runs`, `mutant_results`): written by mutation-testing skill only; never edited
- **Identity layer** (`mutants`): upserted by mutation-testing skill; never deleted
- **State layer** (`gap_ledger`): patched by humans and agents; mutation-testing skill updates `open`/`fixed` only
- **Lifetime:** indefinite; one SQLite + one JSONL per project slug
- **Conflict resolution:** JSONL is append-only; SQLite uses `INSERT OR REPLACE` / `UPDATE` per layer rules
- **Sunset:** archive to `~/logbooks/mutation-testing/archive/` when the project is retired

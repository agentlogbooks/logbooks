---
schema_version: 2
# schema_version must match evals/evals.json schema_version — bump both together when the schema changes
scope: solo-cross-machine
bindings:
  # GOVERNANCE: This file is a shared repo artifact — permanently read-only once committed.
  # Never edit any address_pattern or binding status here. Store resolved IDs, auth, and
  # active status in a local-only override (e.g. ~/logbooks/code-review/bindings.local.yaml
  # or env vars). Agents must never write back to this file.

  # Per-PR/session file backends — {slug} resolved to PR_REF at runtime
  - driver: sqlite
    label: ledger
    address_pattern: ~/logbooks/code-review/{slug}.sqlite
    note: contains hotspots + candidate_findings tables; {slug} = PR_REF resolved at runtime

  - driver: jsonl
    label: run-log
    address_pattern: ~/logbooks/code-review/{slug}.jsonl
    note: append-only trace; record_type one of run|hotspot|candidate|decision|output; {slug} = PR_REF

  # Optional human-facing exports — not authoritative
  - driver: airtable
    label: review-outputs-export
    address_pattern: airtable://appPLACEHOLDER/tblREVIEW_OUTPUTS_PLACEHOLDER?pat_env=AIRTABLE_PAT
    status: pending-auth
    mode: export-only

  - driver: google_sheets
    label: review-outputs-export
    address_pattern: gsheets://SPREADSHEET_ID_PLACEHOLDER/review_outputs?gws_account_env=GWS_ACCOUNT
    status: pending-auth
    mode: export-only
---

# Code Review Logbook v2

Per-PR structured store for deep code review runs. Separates four concerns that v1 mixed together:

1. **Trace** — what happened in one run (JSONL)
2. **Judgment** — what the model believed during that run (`candidate_findings`)
3. **Planning** — which units were selected for review (`hotspots`)
4. **Presentation** — which candidates were surfaced (`surfacing_state`)

## Physical stores

- **Per-PR SQLite** — `~/logbooks/code-review/{PR_REF}.sqlite` — `hotspots` + `candidate_findings`
- **Per-run JSONL** — `~/logbooks/code-review/{PR_REF}.jsonl` — append-only trace

Airtable and Google Sheets are optional **export-only** views. They are not the source of truth.

## Design principles

- Hotspots are the planning unit — not angles.
- Candidate findings are ephemeral judgments from one run.
- `detection_state` + `surfacing_state` replace the v1 single `status` field.
- `priority_score` (multi-factor formula) replaces the v1 `severity × confidence` score.
- Root-cause `fingerprint` replaces line-number-based deduplication.

---

## Tables

### hotspots

One row per risky changed unit selected for focused review in a run.

| Column | Type | Notes |
|--------|------|-------|
| hotspot_id | text PK | Unique hotspot id, e.g. `{RUN_ID}-hs-1` |
| run_id | text NOT NULL | Identifies which run selected this hotspot |
| hotspot_key | text NOT NULL | Stable within-run key, e.g. `src/auth.ts::updateUser`; UNIQUE per run |
| file_path | text NOT NULL | Path to changed file |
| symbol | text | Nullable — function/method/class name if applicable |
| line_start | integer | Nullable |
| line_end | integer | Nullable |
| summary | text NOT NULL | Why this unit was selected and what changed |
| change_archetypes_json | text NOT NULL DEFAULT '[]' | JSON array of archetype strings |
| risk_tags_json | text NOT NULL DEFAULT '[]' | JSON array of risk dimension names |
| why_selected | text NOT NULL | Human-readable selection rationale |
| lenses_json | text NOT NULL DEFAULT '[]' | JSON array of lens names assigned to this hotspot; updated in Phase 3 after lens selection |

**Always-on lenses** (included in every hotspot's `lenses_json`): `correctness`, `maintainability`

### candidate_findings

Judgments produced by hotspot subagents. May be surfaced, dropped, or deduplicated.

| Column | Type | Notes |
|--------|------|-------|
| candidate_id | text PK | Unique candidate id |
| run_id | text NOT NULL | |
| hotspot_id | text NOT NULL FK | References `hotspots.hotspot_id` — NOT NULL enforced |
| output_type | enum NOT NULL | `finding / question` |
| issue_class | text NOT NULL | Machine-readable class, e.g. `auth-boundary-regression` |
| fingerprint | text NOT NULL | Root-cause fingerprint for semantic dedup |
| summary | text NOT NULL | Reviewer-facing summary |
| evidence | text NOT NULL | What in the diff/context supports this |
| why_now | text NOT NULL | What changed that created this risk |
| file_path | text | Nullable |
| line_start | integer | Nullable |
| line_end | integer | Nullable |
| severity | enum NOT NULL | `info / low / medium / high / critical` |
| confidence_local | real NOT NULL | 0.0–1.0, confidence from diff/context alone; CHECK BETWEEN 0.0 AND 1.0 |
| confidence_context | real NOT NULL | 0.0–1.0, confidence including wider codebase context; CHECK BETWEEN 0.0 AND 1.0 |
| actionability | enum NOT NULL | `low / medium / high` |
| blast_radius | enum NOT NULL | `local / module / service / public-contract` |
| priority_score | integer NOT NULL | 0–100 (see Priority model); CHECK BETWEEN 0 AND 100 |
| detection_state | enum NOT NULL | `candidate / selected / dropped / duplicate-in-run / already-on-pr` |
| surfacing_state | enum NOT NULL | `pending / suppressed / posted / question-only` |
| drop_reason | text | Nullable — reason if `detection_state = dropped` |
| suggested_fix | text | Nullable — optional concise fix direction from subagent |
| current_model | text NOT NULL | Model that produced this candidate |
| created_at | text | ISO 8601 datetime |

---

## States

### detection_state

What happened during reasoning?

- `candidate` — raw output from subagent, not yet evaluated
- `selected` — survived skeptic pass and confidence gates
- `dropped` — killed by skeptic pass; see `drop_reason`
- `duplicate-in-run` — same fingerprint as stronger candidate in this run
- `already-on-pr` — existing PR review comment already covers this root cause

### surfacing_state

What happened when deciding whether to show it?

- `pending` — selected but not yet decided on surfacing
- `suppressed` — excluded from report by comment budget
- `posted` — included in the surfaced items report
- `question-only` — surfaced as a question, not a finding

---

## Priority model

### Severity weights

| severity | weight |
|----------|--------|
| critical | 1.0 |
| high | 0.8 |
| medium | 0.5 |
| low | 0.2 |
| info | 0.05 |

### Actionability weights

| actionability | weight |
|---------------|--------|
| high | 1.0 |
| medium | 0.6 |
| low | 0.2 |

### Blast-radius weights

| blast_radius | weight |
|--------------|--------|
| public-contract | 1.0 |
| service | 0.8 |
| module | 0.6 |
| local | 0.3 |

### Noise penalty

| situation | penalty |
|-----------|---------|
| default | 0.00 |
| partial overlap or weaker evidence | 0.10 |
| likely convention/preference-driven | 0.25 |
| materially speculative but retained as question | 0.40 |

### Formula

```
priority_score = round(100 × (
  0.45 × severity_weight
  + 0.25 × confidence_local
  + 0.10 × confidence_context
  + 0.10 × actionability_weight
  + 0.10 × blast_radius_weight
  − noise_penalty
))
```

Clamp to 0..100.

---

## SQLite initialization

```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite "
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS hotspots (
  hotspot_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  hotspot_key TEXT NOT NULL,
  file_path TEXT NOT NULL,
  symbol TEXT,
  line_start INTEGER,
  line_end INTEGER,
  summary TEXT NOT NULL,
  change_archetypes_json TEXT NOT NULL DEFAULT '[]',
  risk_tags_json TEXT NOT NULL DEFAULT '[]',
  why_selected TEXT NOT NULL,
  lenses_json TEXT NOT NULL DEFAULT '[]',
  UNIQUE(hotspot_key, run_id)
);
CREATE TABLE IF NOT EXISTS candidate_findings (
  candidate_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  hotspot_id TEXT NOT NULL REFERENCES hotspots(hotspot_id),
  output_type TEXT NOT NULL CHECK(output_type IN ('finding','question')),
  issue_class TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence TEXT NOT NULL,
  why_now TEXT NOT NULL,
  file_path TEXT,
  line_start INTEGER,
  line_end INTEGER,
  severity TEXT NOT NULL CHECK(severity IN ('info','low','medium','high','critical')),
  confidence_local REAL NOT NULL CHECK(confidence_local BETWEEN 0.0 AND 1.0),
  confidence_context REAL NOT NULL CHECK(confidence_context BETWEEN 0.0 AND 1.0),
  actionability TEXT NOT NULL CHECK(actionability IN ('low','medium','high')),
  blast_radius TEXT NOT NULL CHECK(blast_radius IN ('local','module','service','public-contract')),
  priority_score INTEGER NOT NULL CHECK(priority_score BETWEEN 0 AND 100),
  detection_state TEXT NOT NULL CHECK(detection_state IN ('candidate','selected','dropped','duplicate-in-run','already-on-pr')),
  surfacing_state TEXT NOT NULL CHECK(surfacing_state IN ('pending','suppressed','posted','question-only')),
  drop_reason TEXT,
  suggested_fix TEXT,
  current_model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hotspots_run_id ON hotspots(run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_run_id ON candidate_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_fingerprint ON candidate_findings(fingerprint);
CREATE INDEX IF NOT EXISTS idx_candidates_hotspot_id ON candidate_findings(hotspot_id);
"
```

---

## Queries

### Hotspots for a run

```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT hotspot_key, file_path, symbol, summary, risk_tags_json, lenses_json
   FROM hotspots
   WHERE run_id = '20260420-101530-a1b2c3';"
```

### Surviving candidates sorted by priority

```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT candidate_id, output_type, issue_class, summary, severity, priority_score,
          surfacing_state
   FROM candidate_findings
   WHERE run_id = '20260420-101530-a1b2c3'
     AND detection_state = 'selected'
   ORDER BY priority_score DESC;"
```

### Full audit trail (all candidates including dropped)

```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT c.candidate_id, c.output_type, c.severity, c.detection_state,
          c.surfacing_state, c.drop_reason, c.priority_score, c.summary,
          h.hotspot_key
   FROM candidate_findings c
   JOIN hotspots h ON h.hotspot_id = c.hotspot_id
   WHERE c.run_id = '20260420-101530-a1b2c3'
   ORDER BY c.priority_score DESC;"
```

### Find by fingerprint (dedup check)

```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT candidate_id, summary, detection_state, priority_score
   FROM candidate_findings
   WHERE fingerprint = 'auth-boundary-regression|updateUser|authorization-preserved|public-endpoint'
     AND run_id = '20260420-101530-a1b2c3';"
```

### JSONL: top surfaced items by priority

```bash
grep '"record_type":"output"' ~/logbooks/code-review/pr-123.jsonl \
  | jq -s 'sort_by(-.priority_score) | .[] | {priority_score, output_type, severity, summary, file_path}'
```

### JSONL: all decisions for a run

```bash
grep '"record_type":"decision"' ~/logbooks/code-review/pr-123.jsonl \
  | jq -s '.[] | select(.run_id == "20260420-101530-a1b2c3") | {candidate_id, detection_state, surfacing_state, drop_reason, priority_score}'
```

---

## JSONL record types

All JSONL writes use `jq -nc` with named `--arg`/`--argjson` parameters — never raw shell interpolation on free-form text fields.

| record_type | Written in phase | Key fields |
|-------------|-----------------|------------|
| `run` | Phase 0 | run_id, repo_slug, pr_ref, review_target_type, diff_hash, current_model, skill_version, started_at |
| `hotspot` | Phase 2 | run_id, hotspot_id, hotspot_key, file_path, symbol, summary, change_archetypes, risk_tags, why_selected |
| `candidate` | Phase 5 | run_id, candidate_id, hotspot_id, output_type, issue_class, fingerprint, summary, evidence, why_now, severity, confidence_local, confidence_context, actionability, blast_radius |
| `decision` | Phase 9 | run_id, candidate_id, detection_state, surfacing_state, drop_reason, priority_score |
| `output` | Phase 9 | run_id, candidate_id, pr_ref, output_type, severity, summary, file_path, line_start, line_end, priority_score |

(Lenses are written to SQLite only — Phase 3 UPDATE sets `lenses_json`; no separate JSONL record is written for lens selection.)

---

## Corrections

Both tables are append-only; no rows are ever patched in place.

### hotspots
Append-only; no in-place correction; new runs produce new rows.

### candidate_findings
Append-only; superseded candidates are marked via `detection_state`, not deleted or patched.

## Partial rows

Convention per record type.

### hotspots
Nullable fields (`symbol`, `line_start`, `line_end`) use SQL NULL; all NOT NULL fields must be present at insert time.

### candidate_findings
Nullable fields (`file_path`, `line_start`, `line_end`, `drop_reason`, `suggested_fix`) use SQL NULL; no empty-string convention.

## Governance

- **Owner:** logbook-creator / deep-code-review skill author
- **Access:** append by deep-code-review skill agents; read by humans and downstream agents
- **Lifetime:** indefinite; one SQLite file and one JSONL file per PR_REF
- **Conflict resolution:** SQLite transactions for the ledger; JSONL is append-only (no conflict possible)
- **Sunset:** archive (move to `~/logbooks/code-review/archive/`) when the PR is closed and no further review runs are expected

## Cloud export

Airtable and Google Sheets may be used as human-facing views — **one-way exports only**.

Recommended fields for surfaced outputs:
`pr_ref`, `run_id`, `output_type`, `severity`, `priority_score`, `issue_class`, `summary`, `file_path`, `line_start`, `line_end`, `surfacing_state`, `current_model`, `created_at`

Once `status: active` — export to Google Sheets (13 columns A–M):
```bash
gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"SPREADSHEET_ID_PLACEHOLDER","range":"review_outputs!A1","valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"}' \
  --json '{"values":[["pr-123","20260420-101530-a1b2c3","finding","high","92","auth-boundary-regression","Guard removed from updateUser","src/auth.ts","42","57","posted","claude-sonnet-4-6","2026-04-20"]]}'
# Columns A–M: pr_ref, run_id, output_type, severity, priority_score, issue_class, summary, file_path, line_start, line_end, surfacing_state, current_model, created_at
```

---

## Migration from v1

| v1 | v2 |
|----|----|
| `angles` table | `hotspots` table |
| `findings` table | `candidate_findings` table |
| `findings.status` (one field) | `detection_state` + `surfacing_state` (two fields) |
| `score = severity × confidence` | `priority_score` (multi-factor formula) |
| Line-number dedup | Root-cause fingerprint dedup |
| Per-angle web research | Built-in lens packs + conditional targeted search |
| `angle_id` FK | `hotspot_id` FK (NOT NULL) |

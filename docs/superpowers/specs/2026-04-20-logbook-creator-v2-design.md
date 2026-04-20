# logbook-creator v2 Design

Upgrade the logbook-creator skill from a flat-schema designer into a memory architect — one that models entities, lifecycles, and authority before it models columns and files.

## Problem

The v1 skill is strong at deciding whether a logbook is warranted (Steps 1–2.3, the three-of-four qualification test, usage commitment). It is weak at deciding what kind of logbook architecture a workflow actually needs.

The root cause: v1 jumps from usage commitment directly to column design (Step 3), assuming every job fits one table, one schema, one correction rule, one storage format. That assumption breaks for serious agent workflows, which typically need at least a trace layer, a ledger layer, and sometimes a feedback layer — with different mutability rules for each.

The symptom: the earlier code-review logbook came out as a per-PR findings table with a thin `angles` side table, when the right design was a multi-entity SQLite ledger + JSONL run-trace with four identity layers and two separate state fields.

## Approach

Approach C — targeted structural surgery. Keep what works (Steps 1, 2.1, 2.2, 2.3, anti-patterns, handoff section). Replace what doesn't (Steps 3 and 4, spec template prose for multi-entity). Update concept.md with new sections and softened framing. Migrate the one existing v1 spec in this repo.

Change #10 from the original diagnosis (machine-readable YAML frontmatter with `spec_version`, `logbook_kind`, `primary_store`, `record_types`, `projections`) was evaluated and dropped. `primary_store` is already implied by the binding drivers. `logbook_kind` is inferable from the prose sections. Frontmatter exists in specs only when there are bindings to configure — adding fields for their own sake doesn't earn the complexity cost.

---

## SKILL.md changes

### What stays

- Step 1 — motivation patterns (tracking, staging, human-in-the-loop, multi-agent, collection)
- Step 2.1 — scope, location, lifetime
- Step 2.2 — partitioning
- Step 2.3 — usage commitment
- Anti-patterns catalog
- Handoff-to-skill-creator section

Minor word edits in Step 2 where "schema" appears in a flat-table sense — replace with "memory design" or "record types" so the language doesn't assume single-table before Step 2.4 has run.

### New Step 2.4 — Model the state architecture

Inserted between Step 2.3 and Step 3. Runs before any column design.

Ask seven questions:

1. What are the stable nouns in this workflow? (examples: run, hotspot, issue, candidate, feedback event, source, section)
2. Which are append-only? Which are mutable current state?
3. Does the same real-world thing recur across sessions?
4. Are there raw outputs vs. accepted/surfaced outputs — do they need to live separately?
5. Will humans or agents later accept, fix, dismiss, or suppress entries?
6. Is there a smaller meaningful work unit inside each artifact? (hotspot inside a run, finding inside a hotspot, claim inside a source)
7. What identity layers are needed? (row key / domain fingerprint / run boundary / occurrence)

Output decision: does this job need a **single-table logbook**, a **relational bundle** (SQLite with multiple tables), or an **event-log-plus-ledger pair**?

- Single-table → proceed to Step 3 as before (entity-first framing still applies, but trivially resolves to one entity)
- Multi-entity → Step 3 expands to 3A/3B/3C
- Event-log-plus-ledger → multi-entity with one append-only JSONL trace alongside the SQLite ledger

### Replaced Step 3 — Entity-first schema design

Three sub-steps in sequence:

**3A — Derive record types**
List the tables or record kinds before naming any columns. Examples: `review_runs`, `hotspots`, `candidate_findings`, `issues`, `occurrences`, `feedback_events`. For single-table logbooks this is trivial (one record type), but the question is still asked.

**3B — For each record type, define:**
- Purpose (one sentence)
- Identity key(s): row key, and whether a domain fingerprint or run-boundary key is also needed
- Mutability: append-only or patchable current state
- Partial-row convention: empty string, explicit null, or "unknown" — one per record type
- Correction rule: append-only (new row supersedes) or patch-in-place — aligned with mutability
- Relationships to other record types (foreign keys, hierarchies)

The four schema questions from v1 (identity, partial rows, corrections, field semantics) move here — answered once per record type, not globally.

**3C — Columns**
Only after 3B is settled. Propose a starter set per record type; let the user refine. Include one sentence of field semantics per column.

End Step 3 with the actions question (unchanged from v1): does this logbook need to feed an external system?

### Replaced Step 4 — Primary store + projections

New framing: first establish what is authoritative, then what views exist.

**Authoritative store** — one of: SQLite, CSV, JSONL, spreadsheet, markdown. Same decision table as v1, same rationale. Pick one and document it.

**Projections** (optional) — each labeled with a role:
- `run-trace` — append-only event log alongside the ledger (JSONL); not queryable relationally but preserves the full execution record
- `export-only` — read-only snapshot for human browsing (Google Sheets, Airtable); never the source of truth
- `mirror` — editable copy (rare; creates two-source-of-truth risk; almost always wrong)

The key principle: a projection is derived from the authoritative store. Writes go to the authoritative store. If unclear which is authoritative, the design isn't finished.

### Spec template prose updates

The existing template sections (Address, Storage, Schema, Identity, Partial rows, Corrections, Queries, Validation, Actions, Governance) are preserved for single-table logbooks — no change.

For multi-entity logbooks, the template expands:

- **Storage** becomes **Physical stores** — lists authoritative store + each projection with its role
- **Schema** becomes one `### <RecordType>` subsection per table, each with its own schema table
- **Identity**, **Partial rows**, **Corrections** each become per-record-type subsections
- **Queries** remains flat but includes cross-table JOIN examples where relevant

No new YAML frontmatter fields. The `bindings` block stays as the only structured frontmatter, present only when auth config is needed.

---

## concept.md changes

All existing content stays. Three targeted edits + two new sections + one new worked example.

### Edit 1 — Soften "a logbook is not a log"

Current (line 9): *"A logbook is not a log."*

New framing: *"A logbook is not only a log. Advanced workflows often pair an append-only run trace with a mutable working ledger — the trace captures what happened, the ledger holds current state. What a logbook is not is a log alone: append-only, machine-written, optimized for replay rather than current-state query."*

### Edit 2 — Revise "one logbook, one schema, one job"

Current (line 94 in Principles): *"One logbook, one schema, one job."*

New: *"One job, one coherent memory design. Sometimes that is one table; sometimes it is a small relational bundle with a few related record types. What to avoid is a universal domain schema — not multi-entity designs that genuinely need them."*

### New section — Single-table vs multi-entity

Added under "Row-shaped logbook", before "Anti-patterns".

**Use a single table when:**
- One row type dominates
- Rows don't recur as stable entities across sessions
- No separate trace vs. memory vs. feedback layer

**Use a multi-entity logbook when:**
- The workflow has repeated runs against the same artifact
- Raw outputs differ from accepted/surfaced outputs and need to live separately
- The same real-world thing recurs across sessions (same issue reappears across PRs, same candidate across runs)
- Humans or agents annotate results in a later pass

Rule of thumb: if you'd naturally say "a run has many hotspots, each hotspot has many candidates" — that's a relational bundle, not a flat table. If you'd say "each session has one entry" — it's probably single-table.

### New section — Authoritative store vs projections

Added under "Choosing a storage format".

One store is authoritative; others are views. Three projection kinds:

- **run-trace** — append-only event log alongside the ledger; preserves full execution record; not the source of truth for current state
- **export-only** — read-only snapshot for human browsing (Sheets, Airtable); regenerated from the authoritative store; never edited directly
- **mirror** — editable copy; almost always wrong; creates the "second place to update" anti-pattern

If it's unclear which store is authoritative, the logbook isn't designed yet. The authoritative store is where writes happen; projections are derived from it.

### New worked example — Deep review / multi-phase agent workflow

Added under "Worked examples".

A per-PR code review logbook with two physical stores:

**SQLite ledger** (`~/logbooks/code-review/{PR_REF}.sqlite`):
- `hotspots` — append-only, one row per risky unit selected for review; key: `hotspot_id`
- `candidate_findings` — append-only, one judgment per hotspot per run; key: `candidate_id`

**JSONL run-trace** (`~/logbooks/code-review/{PR_REF}.jsonl`):
- Append-only event log; `record_type` one of run/hotspot/candidate/decision/output
- Preserves full execution record; not queried relationally

Identity has four layers: `run_id` (execution boundary), `hotspot_id` (planning unit within a run), `candidate_id` (one model judgment), `fingerprint` (root-cause hash for semantic dedup across runs).

Both tables are append-only — corrections are never patched in place; a new run produces new rows. Cloud exports (Sheets, Airtable) are export-only projections — not authoritative, regenerated from the SQLite ledger.

The value of the multi-entity design: `detection_state` + `surfacing_state` can be tracked separately per candidate, cross-run dedup works via fingerprint without touching earlier rows, and the run-trace preserves the full reasoning record independently of the current-state ledger.

---

## Migration: `findings.logbook.md`

The existing spec is already richer than v1 — it has multiple tables, state machines, priority model formula, DDL, and detailed query snippets. It was hand-crafted beyond what v1 SKILL.md could produce. Migration adds only the three sections that the new spec template requires but are currently absent.

### Add `## Corrections`

Both tables are append-only. State this explicitly per record type:
- `hotspots` — append-only; no in-place correction; new runs produce new rows
- `candidate_findings` — append-only; superseded candidates are marked via `detection_state`, not deleted or patched

### Add `## Partial rows`

Convention is implicit (nullable columns = SQL NULL) but not stated. Add per record type:
- `hotspots` — nullable fields (`symbol`, `line_start`, `line_end`) use SQL NULL; all NOT NULL fields must be present at insert time
- `candidate_findings` — nullable fields (`file_path`, `line_start`, `line_end`, `drop_reason`, `suggested_fix`) use SQL NULL; no empty-string convention

### Add `## Governance`

Currently entirely missing. Content:
- **Owner:** logbook-creator / deep-code-review skill author
- **Access:** append by deep-code-review skill agents; read by humans and downstream agents
- **Lifetime:** indefinite; one SQLite file and one JSONL file per PR_REF
- **Conflict resolution:** SQLite transactions for the ledger; JSONL is append-only (no conflict possible)
- **Sunset:** archive (move to `~/logbooks/code-review/archive/`) when the PR is closed and no further review runs are expected

No structural changes to existing sections.

---

## Out of scope

- Feedback loops as a first-class pattern (change #7 from the original diagnosis) — the new Step 2.4 question 5 ("will humans or agents later accept, fix, or dismiss entries?") surfaces the need; generating a feedback table automatically is a judgment call left to the skill's conversation, not hardcoded
- Canonicalization / dedup as a design question (change #8) — covered by Step 2.4 question 3 ("does the same real-world thing recur across sessions?") and the new identity-layers question in 3B
- Index/view inference for SQLite (change #9) — the new 3B asks for relationships between record types, which naturally surfaces index candidates; explicit index inference guidance adds prescription without much gain since the DDL in the spec already captures this

These are satisfied at the level of asking the right questions, not at the level of generating boilerplate automatically.

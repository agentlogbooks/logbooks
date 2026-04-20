---
name: logbook-creator
description: Design and create a logbook — a shared, queryable, schema-stable working surface that agents and humans append to, annotate, and query across sessions. Invoke when the user explicitly wants to track structured entries across multiple sessions or multiple contributors (e.g. "I want to track X across sessions", "I need a draft layer before committing to Jira", "let me review what the agent found before applying it", "multiple agents need to collaborate on this"). Also invoke when a document is accumulating repeated structured entries that would be better shaped as rows with named columns. Do NOT invoke for single-session analysis tasks, ad hoc data collection, or when the user asks to "collect" or "gather" information without mentioning cross-session reuse or multiple contributors — those are scratch tasks, not logbook tasks. This skill creates the logbook itself and a spec file — it does NOT create or modify skills. For wiring the logbook into a skill, hand off to skill-creator afterward.
---

# Logbook Creator

## What this skill does

This skill runs a guided conversation that produces two artifacts:

1. **A logbook instance** — the actual storage (CSV, JSONL, SQLite, spreadsheet, or markdown table) with the schema in place.
2. **A logbook spec** — a sibling markdown file (`<logbook-name>.logbook.md`) describing everything needed to operate on that logbook: schema semantics, identity rule, partial-row convention, correction rule, query patterns, validation rules, actions, and governance.

This skill does **not** write SKILL.md files. Wiring the logbook into a skill is skill-creator's job — the spec file is the handoff artifact between the two.

## When a logbook is the right answer

A logbook is shared structured state that outlives a single session. It earns its cost when the state is repeatedly read, written, or queried by different actors across sessions. It is not a document, not a tracker, not a log, and not scratch state. Before proceeding, confirm at least three of the following are true:

- **Multiple contributors** — more than one agent or human reads and writes the same state.
- **Schema-stable structure** — the shape is predictable enough that tools can query it without understanding the content. You can name the columns in under 30 seconds.
- **Tool-queried, not reread** — the common questions are answered by filtering, sorting, or aggregating, not by scanning the whole thing in context.
- **Outlives the session** — the state needs to be readable by a different agent or session later.

If fewer than three hold, push back gently and propose an alternative: a markdown doc, chat state, a typed handoff artifact, or a tracker like Jira. Don't build a logbook the user won't actually need. See `references/concept.md` for the full framing and the anti-patterns to watch for.

## The conversation flow

Run these steps in order. Don't ask every question at once — each step builds on the previous one's answers.

### Step 1 — Understand the motivation

Ask the user what's going on in plain language, not "what columns do you want." Listen for which of these five motivation patterns the situation matches (it may be a blend):

- **Tracking across sessions** — accumulating entries (decisions, observations, feedback) that the same person or a future agent will consult later.
- **Staging before commit** — shaping draft entries (Jira candidates, config changes, content drafts) in a permissive layer before pushing to a strict target system.
- **Human-in-the-loop review** — agents produce structured results and a human reviews, annotates, approves, or rejects before anything is applied downstream.
- **Multi-agent coordination** — several agents read and write the same structured state; the logbook is the shared contract between them (explorer writes findings, critic scores, estimator adds numbers).
- **Collection for later analysis** — gather structured data during work sessions now so that filtering, aggregation, or visualization is cheap later.

Reflect back what you heard in one sentence: *"So this sounds like a staging surface — you want agents to shape candidates, and you review and push approved ones to X. Is that right?"* The motivation shapes everything downstream, especially which validation rules, actions, and governance defaults matter.

**Watch for the hidden logbook:** users sometimes say "I want a planning doc" or "I need a tracking sheet" when what they actually want is rows with structured annotations. If the user describes entries with statuses, scores, owners, or categories, test whether it's a logbook before defaulting to prose.

**Also watch for non-logbook problems.** If the work is truly single-session, single-reader, or still figuring out its shape, don't push a logbook on the user. Say so and suggest the lighter alternative.

### Step 2 — Scope & lifecycle

Before picking columns or a storage format, work through three sub-questions about where this logbook lives, who owns it, and whether it will actually be used. Each sub-question feeds into the next and into downstream steps. Don't collapse these into one prompt — they build on each other, and users often revise their earlier answer once a later one forces the issue. Let them go back.

#### 2.1 Scope, location, lifetime

Ask in three probes, conversationally — not as a form. These three decisions reshape every downstream choice.

**Scope.** *"Is this logbook personal — living on your machine and read mostly by you — or shared — read and written by a team, multiple machines, or committed to a repo?"*

- **Personal** → Location defaults toward `~/.local/state/<name>/`, `~/.claude/skills/<name>/`, or another home-relative path. Governance defaults to single-owner, no access control. Conflict resolution trivial.
- **Shared** → Location defaults toward a repo path or a shared store (Google Sheets, shared SQLite). Governance must name an owner and access policy. Conflict resolution is non-trivial.
- **Ambiguous / blended** → Pick one and document the assumption. Mixed personal/shared is a governance trap; force the user to choose, or split into two logbooks with separate specs.

**Location.** *"Given that, give me an absolute path where this logbook should live."*

Validate the path pattern in conversation (save the filesystem check for Step 5):

- Reject ephemeral-looking paths when lifetime is longer than the session. Patterns that indicate ephemerality: `/tmp/…`, `/private/var/folders/…`, `/sessions/…`, any path under a sandbox or working directory whose stability across sessions is not guaranteed. When detected: call it out and ask the user for a durable path.
- Personal scope + path inside a git repo → warn: *"This will be committed unless gitignored. Do you want that? If not, either move to a home-dir path or plan to add a `.gitignore` rule right now."*
- Shared scope + path only on the local machine (e.g. `~/notes/…`) → warn: *"Only you will have this. To share, pick a committed repo path, a shared drive, or a hosted store."*

If no durable path is available (sandbox, fresh machine, no persistent storage), don't paper over it. Say so explicitly: *"This will be a session-scoped logbook; it won't survive a new shell."* Lifetime collapses to "session" and the Step 1 logbook-vs-scratch check applies again — a session-scoped logbook is usually scratch state.

**Lifetime.** *"How long does this need to be readable? One session, a sprint, a quarter, or indefinite?"*

Lifetime drives governance defaults in Step 5:

- **Session** — no sunset rule needed; logbook is scratch. Reconsider whether a logbook is the right shape at all (see Step 1 anti-pattern).
- **Sprint / quarter** — sunset rule is the end of that window.
- **Indefinite** — archival rule required (move to `archive/` after N days of no writes on a resolved entry, or similar).

End 2.1 with a one-sentence recap: *"So this is a personal|shared logbook at `<path>` that should last `<lifetime>`. Confirm before we partition."*

#### 2.2 Partitioning

*"One file holding all entries, or one file per X?"*

Present three common patterns tied back to the motivation from Step 1:

| Pattern | Fits | Filename shape | Notes |
|---|---|---|---|
| Single growing file | Tracking/staging motivations with one topic and modest volume | `<name>.<ext>` | Simplest. Good default. |
| One file per problem/topic | Multi-agent or debugging work where each topic has its own arc | `{YYYY-MM-DD}-{slug}.{ext}` (date = file creation) | Cross-topic queries become `csvstack *.csv` or globs. Columns that name the topic (`problem_id`, `topic`) become redundant and should be dropped. |
| One file per time window | High-volume or short-lived scopes (daily standup log, weekly retro) | `{YYYY-MM-DD}.{ext}` or `{YYYY-W##}.{ext}` | Similar effect on columns: drop `session` or `week`. |

Decision rule: if the user answers "one file per X," the filename scheme AND the redundant-column list are decided **here**, not in Step 3. Step 3 reads these answers and drops the redundant columns from each record type's schema, adding a one-line note below each affected table naming each dropped column and why.

Mixed partitioning (some entries shared, some personal; some per-topic, some global) is out of scope. Push the user to pick one, or to split into two logbooks with separate specs.

End 2.2 with the filename shape confirmed on an example path built from the 2.1 answer — e.g., *"So entries will live at `/Users/alice/.local/state/debug-log/2026-04-15-flaky-api-tests.csv`. Confirm."*

#### 2.3 Usage commitment

The hardest sub-step. The concept warns: *"Creating a logbook nobody reads"* is the most common anti-pattern. 2.3 is the upfront check for it.

Ask two questions, both requiring **concrete** answers:

**Append moment.** *"Walk me through the very next time you'd add an entry. When (what time of day, what trigger), by whom, and what prompts you to open the file?"*

Good answers are specific: *"Next debugging session, after I try a fix and it fails, I run `append-attempt`."* Bad answers are vague: *"Eventually, when I think of something."*

**Query moment.** *"Now walk me through the next time you'd read or filter entries. When, by whom, and what decision does the query inform?"*

Good answers: *"Before I start on a flaky-test problem, I run `query-before-trying` to avoid repeating approaches."* Bad answers: *"For reference sometime," "if I need it later."*

If either answer is vague, push back with one of:

- **Redirect to a lighter alternative.** *"That sounds like what a markdown doc / chat state / Jira ticket gives you. Want that instead?"*
- **Sharpen the motivation.** *"If you can't picture concretely appending or querying, reconsider: is this tracking, or would a short prose doc be a better fit?"*
- **Commit to a trial.** *"Let's build a minimal version anyway — but the sunset rule is `if no entries in 2 weeks, archive.` Agree to that?"*

Proceed to Step 3 when both the append and query moments are concrete, or after an explicit commit-to-trial with the sunset rule recorded in governance. If the user cannot describe either moment concretely and declines the trial option, recommend a lighter alternative (markdown doc, chat state) and stop.

If the user insists on the logbook despite vague answers, proceed — but record the vague answers verbatim in the spec's `## Governance` as *"Usage pattern not yet articulated; revisit after first week. Sunset after 14 days of no writes."* This documents the exception so a future reader can see the upfront check was skipped intentionally.

#### 2.4 State architecture

Before picking columns or tables, decide what kinds of state this workflow actually produces. Serious agent workflows often need more than one record type — a raw trace layer, a mutable ledger, a feedback layer — with different mutability rules. Skipping this step locks you into one-table-fits-all and forces bad trade-offs in Step 3.

Ask these seven questions in conversation (not as a form):

1. **Stable nouns** — *"What are the stable nouns in this workflow? Things like runs, hotspots, issues, candidates, feedback events, sources, sections — whatever the user's vocabulary names."*
2. **Append-only vs mutable** — *"Which of those are append-only (a new occurrence is a new row) and which hold mutable current state (the same thing gets updated as work progresses)?"*
3. **Cross-session recurrence** — *"Does the same real-world thing recur across sessions? The same issue reappears across PRs; the same candidate comes back in another run. If yes, a domain fingerprint is needed alongside the row key."*
4. **Raw vs surfaced outputs** — *"Are there raw model outputs and accepted/surfaced outputs? If so, do they need to live separately so dropped-but-reviewable candidates don't get thrown away?"*
5. **Later annotation** — *"Will humans or agents later accept, fix, dismiss, or suppress entries? If yes, there's either a feedback record type or a state field on the existing record type."*
6. **Smaller work units** — *"Is there a smaller meaningful work unit inside each artifact — a hotspot inside a run, a finding inside a hotspot, a claim inside a source? Nested hierarchies surface here."*
7. **Identity layers** — *"What identity layers does this workflow need? The common four are row key (unique per row — often one per record type in multi-entity designs), run-boundary key (scopes rows to an execution), domain fingerprint (a hash of the root-cause concept — enables semantic dedup across runs), and occurrence (how often the same fingerprint has appeared — tracked by fingerprint-count queries, not a separate column). Not every workflow needs all four."*

**Output decision.** Name whether this job needs a **single-table logbook** or a **multi-entity logbook**:

- **Single-table** → one record type dominates and the other questions collapse to "not really." Step 3 passes through 3A/3B trivially (one record type) and lands in 3C with a flat schema.
- **Multi-entity** → several stable nouns with different mutability rules, or raw-vs-surfaced separation, or cross-session recurrence. Step 3A names several record types, 3B iterates per type, 3C produces per-table columns.

Whether a multi-entity logbook also needs an append-only JSONL run-trace alongside its SQLite ledger is a Step 4 question (projections), not a separate branch here.

### Step 3 — Entity-first schema design

By this point Step 2.4 has decided whether this is a single-table or a multi-entity logbook. Both paths run through the same three sub-steps — single-table collapses them trivially (one record type) while multi-entity fans them out per record type.

Two answers from earlier still shape what gets recorded:

- **Partitioning (2.2).** If the user chose one file per X, drop columns whose values are encoded in the filename (`problem_id`, `session`, `topic`, `date`, `week`, etc.) from every record type that would otherwise include them. Annotate their absence with a one-line note under the affected table: *"Column `<name>` is encoded in the filename, not stored."* Keeping the column in a record type's schema and the filename both is redundant and invites drift.
- **Scope (2.1).** If the logbook is shared, `author` (or equivalent) is a required column on any record type a human or external agent writes. If personal, `author` can be optional and defaults to the single owner recorded in governance.

#### 3A — Derive record types

List the tables or record kinds before naming any columns. Examples: `review_runs`, `hotspots`, `candidate_findings`, `issues`, `occurrences`, `feedback_events`. For single-table logbooks this is trivial — one record type — but ask the question anyway so the decision is recorded rather than assumed.

#### 3B — For each record type, define

Answer each of these once per record type, grounded in the user's scenario rather than abstractly:

- **Purpose** — one sentence: what this record type is for.
- **Identity key(s)** — the row key. If Step 2.4 surfaced cross-session recurrence, add a domain fingerprint. If the record type is run-scoped, add a run-boundary key as well.
- **Mutability** — append-only or patchable current state. This usually falls out of the motivation: audit-sensitive record types append; refinement-heavy ones patch.
- **Partial-row convention** — empty string, explicit null, or "unknown". One convention per record type. Mixed conventions corrupt filters.
- **Correction rule** — append-only (new row supersedes) or patch-in-place. Must be consistent with mutability: append-only types correct by appending; patchable types correct by patching.
- **Relationships** — foreign keys into other record types, parent/child hierarchies, any cross-table link.
- **Suggested indexes** — for SQLite backends, propose indexes based on the expected query patterns for this record type (skip for CSV/JSONL).

If two contributors might mean different things by the same column name (`priority`, `status`, `score`), write one sentence of field semantics so the meaning is explicit — define it now, before 3C drafts the columns.

#### 3C — Columns

Only after 3B is settled. Propose a starter set per record type; let the user refine. Include one sentence of field semantics per column. If the schema for any record type can't be described in under 30 seconds, trim or reshape before proceeding.

Also ask one actions question here while the motivation is fresh: *"Does this logbook need to feed an external system — Jira, Miro, a report, another agent? If so, name it."* Record the answer. This populates the `## Actions` section in Step 5 with real content instead of a placeholder. If the user says no external system, write "No actions defined." in the spec.

### Step 4 — Primary store + projections

First establish what is authoritative, then what views exist. One store is the source of truth; everything else is a derived view.

#### Authoritative store

Pick the format that fits the data and the downstream experience, not by default. Make one recommendation with a one-sentence rationale; let the user override.

| Format | When to pick it |
|---|---|
| **CSV** | Flat columns, short values, single writer at a time, want to open in Excel or grep from bash. Good default for ideation, flat decision logs, feedback collectors. Easy to chart later. |
| **JSON Lines (.jsonl)** | Optional or nested fields, schema varies row to row. Still appendable and greppable. Weak if you want column CLI ops. |
| **SQLite** | Need real queries (joins, aggregates, GROUP BY), row volume over a few thousand, multiple logbooks reference each other, concurrent writers, or a multi-entity design from 3A. Loses plain-text inspectability. |
| **Spreadsheet** (Google Sheets, Excel) | Humans are primary editors or reviewers. Visual sorting, filtering, comments. Ideal for human-in-the-loop review. |
| **Markdown table** | Tiny (under ~20 rows), hand-maintained, read more than written. Rarely right for agent-written logbooks. |

Narrow the table by the location picked in 2.1:

- **Inside a shared git repo** → prefer plain CSV, JSONL, or Markdown. They are diffable and reviewable in PRs. Deprioritize SQLite (binary, review-hostile) and spreadsheets (not in the repo at all) — unless you have concurrent writers or a multi-entity design, in which case SQLite's transaction safety and relational queries outweigh the diff cost.
- **Under a home-dir or local-state path** → all formats in the table remain viable. Pick on motivation and data shape.

The motivation biases the choice: staging and collection lean toward CSV or SQLite (diffable, chartable); human-review leans toward spreadsheet; multi-agent concurrent writers and anything multi-entity lean toward SQLite.

Migration is always available — start simple, upgrade when the pain signals (nested fields → JSONL; need joins → SQLite; need human UI → spreadsheet). Tell the user this so they don't over-engineer up front.

#### Projections (optional)

A projection is a view derived from the authoritative store. Writes go to the authoritative store; projections are appended or regenerated alongside it. Each projection has one of three roles:

- **run-trace** — append-only event log alongside the ledger (typically JSONL). Preserves the full execution record; not queryable relationally. Use this when the skill needs to preserve intermediate reasoning or event-level detail that the authoritative ledger tables don't capture — even when the ledger itself is append-only.
- **export-only** — read-only snapshot for human browsing (Google Sheets, Airtable, a rendered report). Regenerated from the authoritative store; never edited directly; never the source of truth.
- **mirror** — editable copy. Almost always wrong — it creates the "second place to update" anti-pattern. Flag it and push back unless the user has a specific operational reason.

If it is unclear which store is authoritative, the design is not finished. Ask again before moving on.

### Step 5 — Create the two artifacts

Before writing either file, re-verify the absolute path from 2.1 is writable and non-ephemeral. Run `test -w "$(dirname '<path>')" && echo ok || echo not-writable` to confirm the parent directory is writable. If the path matches an ephemeral pattern (`/tmp/…`, `/private/var/folders/…`, `/sessions/…`, or any sandboxed working directory), stop and ask once more, even if the user insisted during 2.1.

The spec's `## Address` section must carry the absolute path from 2.1 and the line *"When the user moves this file, update the address here."* — this is already in the template below; do not drop it.

Write both files to the user's selected folder (or to the workspace if no folder is specified). Names:
- `<logbook-name>.<ext>` — the logbook instance (e.g., `retro-observations.csv`).
- `<logbook-name>.logbook.md` — the spec.

For a spreadsheet backend, the "logbook instance" step is a set of setup instructions (headers to paste, column types to set) rather than a file — spell them out clearly in the spec and in your message.

**If any binding has `status: pending-auth`** (cloud backends requiring credentials), also write a third file:
- `<logbook-name>.logbook.local.yaml.template` — committed to the repo as a safe example showing the shape of local overrides (placeholder values only, no real IDs or emails).

Then tell the user: *"Copy `<name>.logbook.local.yaml.template` to `<name>.logbook.local.yaml`, fill in your real IDs, and add `*.logbook.local.yaml` to your `.gitignore`. Never edit the spec file (`*.logbook.md`) to activate a binding."*

When writing a spec with `pending-auth` bindings, always add this comment block immediately before the bindings section:
```yaml
# GOVERNANCE: This file is permanently read-only once committed.
# Never edit address or status here — store resolved config in a local gitignored override.
```

The template must follow this structure:
```yaml
# <name>.logbook.local.yaml — LOCAL OVERRIDES (never commit this file)
# Copy from <name>.logbook.local.yaml.template and fill in real values.
bindings:
  - driver: <driver>
    label: <label>
    address: <driver>://<PLACEHOLDER_ID>/<PLACEHOLDER_TABLE>?<auth_param>=<PLACEHOLDER>
    status: active
# Environment variables: list any env vars referenced in address fields
```

For SQLite, create the database file with the table defined and a companion `_meta` table containing schema, identity rule, partial-row convention, correction rule, owner, and lifetime. Also write the human-readable spec alongside.

## Spec file format

The spec is the handoff artifact for skill-creator and for any human reading the logbook later. Follow this template. Do not omit sections — if a section doesn't apply, say so explicitly in one line so future readers know the decision was deliberate.

```markdown
# Logbook: <name>

<one-sentence job description — what this logbook is for and who uses it>

## Address

<absolute file path, database path + table name, or spreadsheet share link>

When the user moves this file, update the address here.

## Storage

<format + one-sentence rationale for why this format fits the job>

## Schema

| Column | Type | Required | Semantics |
|---|---|---|---|
| id | integer | yes | Auto-incremented row identifier, stable across edits. |
| ... | ... | ... | ... |

## Identity

<rule: auto-increment, natural key of (X, Y), or UUID — and how new entries get their ID>

## Partial rows

<convention for missing fields: empty string, explicit null, or "unknown">

## Corrections

<patch-in-place OR append-correction — with one-sentence rationale tied to the job>

## Queries

Concrete, working snippets against this logbook's actual address. Group by intent.

### Filter by <column>
<bash/python/SQL one-liner that works against the actual file>

### Sort by <column>
<working snippet>

### Aggregate / group by <column>
<working snippet>

### Summary stats
<working snippet>

## Validation

<what "ready" means for an entry — required fields for commit, review completeness checks, etc. Include a snippet that finds incomplete entries.>

## Actions

For each external system this logbook feeds:

### <action name — e.g., commit-to-jira>
- **Purpose:** <one sentence>
- **Readiness check:** <what must be true of a row before it can be acted on>
- **Dry-run:** <how to preview without side effects>
- **Effect:** <what happens in the target system>
- **Patch-back:** <what column gets updated on the source row, e.g., `jira_ticket_id`>

If no actions are defined yet, state that explicitly.

## Governance

- **Owner:** <person or role>
- **Access:** <who can append, who can patch, who can read>
- **Lifetime:** <sprint / quarter / indefinite>
- **Conflict resolution:** <last-write-wins via git, spreadsheet native, SQLite transactions, etc.>
- **Sunset rule:** <when lifetime expires: archive, collapse to summary doc, or renew>
```

The query snippets must be the **actual commands** that work against the logbook as created — not abstract examples. If the logbook is at `/work/retro.csv`, the filter snippet should be a working `awk` or `python` call against that exact path. This is what makes the spec directly consumable by skill-creator.

### Multi-entity variant

When Step 2.4 decided this is a multi-entity logbook, extend the template above as follows. Sections not listed here stay identical to the single-table template.

- **Storage** becomes **Physical stores** — lists the authoritative store first, then each projection with its role (`run-trace`, `export-only`, `mirror`) and address.
- **Schema** becomes one `### <RecordType>` subsection per table, each with its own schema table.
- **Identity**, **Partial rows**, **Corrections** each become per-record-type subsections, one block per record type — so a reader can see the full contract for one table without scanning the whole spec.
- **Queries** remains flat but includes cross-table JOIN examples where relevant.

No new YAML frontmatter fields. The `bindings` block remains the only structured frontmatter, present only when auth config is needed.

Example skeleton for the expanded sections (record type names are illustrative — substitute the ones derived in 3A):

````markdown
## Physical stores

- **Authoritative:** <format> at `<absolute path or address>` — <one-sentence rationale>
- **Projection: <label>** — role: `run-trace` | `export-only` | `mirror` — at `<address>` — <purpose>

## Schema

### <record_type_1>

| Column | Type | Required | Semantics |
|---|---|---|---|
| ... | ... | ... | ... |

### <record_type_2>

| Column | Type | Required | Semantics |
|---|---|---|---|
| ... | ... | ... | ... |

## Identity

### <record_type_1>
<rule>

### <record_type_2>
<rule>

## Partial rows

### <record_type_1>
<convention>

### <record_type_2>
<convention>

## Corrections

### <record_type_1>
<rule>

### <record_type_2>
<rule>
````

## Handoff to skill-creator

After the two files are written, tell the user what to do next. Typical next steps:

- *"Want to wire this into a new skill? Run skill-creator and point it at the spec — it'll generate a SKILL.md that uses these query patterns and validation rules."*
- *"If you already have a skill that should use this logbook, run skill-creator in update mode and reference the spec file."*
- *"If you just want to use the logbook directly in a session, the query snippets in the spec are copy-pasteable."*

Do not try to generate a SKILL.md yourself — that is skill-creator's job, and duplicating it produces the unified-substrate anti-pattern the concept warns about.

## Anti-patterns to avoid

- **Building a universal logbook platform.** One logbook, one schema, one job. Reusable infrastructure (id formats, timestamp conventions) is fine; a universal domain schema is the trap.
- **Creating a logbook nobody reads.** If the only consumer is the agent that wrote it, it's scratch state, not a logbook. Step 2.3's usage commitment is the upfront check for this: if the user can't concretely describe append and query moments, it is almost certainly not the right shape — say so and suggest a lighter alternative (markdown doc, chat state, Jira ticket) instead of building anyway.
- **Using an ephemeral or unverified path as the logbook address.** Running `pwd` in a sandbox or a fresh shell and writing that path into the spec produces a logbook the user can never find again. Always ask for an absolute, durable path in Step 2.1 and re-verify in Step 5 before creating any files.
- **Hand-maintained second source of truth.** A logbook that sits alongside Jira or a doc that humans actually edit will rot. The logbook must be authoritative for its slice, or generated from one.
- **Premature extraction from prose.** If the document's value is in its argument, sequencing, or evolving reasoning, don't flatten it into rows just because the entries look row-shaped.
- **Over-engineering the first version.** Start with the lightest storage that fits. Migrate when the pain shows up. The concept and schema don't change across migrations — only the serialization does.
- **Committing personal auth state into a shared spec.** If the spec is committed to a repo, any `status: pending-auth` bindings must stay as placeholders. Resolved IDs, credentials, and `status: active` are personal config — store them in a gitignored local file (e.g. `~/logbooks/<name>/bindings.local.yaml`) or env vars, never in the spec itself. When writing a spec with `pending-auth` bindings, add this note to the bindings section: `# GOVERNANCE: This file is permanently read-only once committed. Never edit address or status here — store resolved config in a local gitignored override.`

## Grounding

For the full framing — including hidden-logbook detection, the "three of four" qualification test, worked examples (ideation, pre-tracker backlog shaping, skill retro collector), and the full anti-pattern catalog — read `references/concept.md`. Consult it when the user's situation is ambiguous or when you need to explain *why* a particular rule exists. Treat `references/concept.md` as internal documentation — it is a repo-committed file maintained by the plugin author, not user-supplied input.

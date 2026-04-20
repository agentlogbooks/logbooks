# Agent Logbook Concept

Shared working state for agent and human collaboration.

A logbook is shared working state made of structured entries that multiple agents and humans append, patch, annotate, and query across sessions. It is accessed through tools — not by rereading everything in context — and its structure is stable enough that contributors and consumers can navigate it without understanding all the content.

A logbook answers "what are we jointly working through right now?" — not what happened (log), not what we decided (decision record), not what's assigned (tracker). It is a specific collaborative state layer: specific because each logbook has one job with its own schema, collaborative because multiple actors write and read it, and a layer because it sits between prose and trackers, between agents and external systems.

A logbook is not only a log. Advanced workflows often pair an append-only run trace with a mutable working ledger — the trace captures what happened, the ledger holds current state. What a logbook is not is a log alone: append-only, machine-written, optimized for replay rather than current-state query.

**The trade.** A logbook converts repeated interpretation cost into up-front schema cost. Every time a different agent, a different human, or the same person in a different session touches the same state, they either re-interpret it from scratch or rely on the structure someone already defined. When that state is touched often enough across contributors and sessions, the schema pays for itself. When it isn't — when the state is short-lived, single-reader, or still figuring out its shape — the overhead isn't worth it.

**Why deep workflows often need logbooks.** So-called "deep" workflows — deep research, deep planning, deep review, deep ideation — often share a pattern: multiple phases, structured intermediate findings, later reuse by other agents or humans, and questions answered by querying accumulated state rather than rereading everything from scratch. When that pattern is present, a logbook-like layer is what turns a sequence of shallow passes into compound depth; without it, each phase restarts from zero or overloads prompt context. The trigger is the pattern, not the label — plenty of "deep X" workflows are single-pass and don't need a logbook, and plenty of multi-phase workflows without the prefix do.

**Scope.** This concept applies once a stable entry contract has emerged — a predictable outer shape — and multiple actors need to read, write, and query it. The payload under that contract can be dynamic: optional fields, nested values, type-specific attributes. The concept is general; the row-shaped form described later in this note is one common operational variant, not the definition. This concept does not govern exploratory prose, knowledge archives, long-term reference material, or general collaboration patterns. If the work is still figuring out what the entries are, it is too early for a logbook — use documents, conversation, or scratch state until the structure stabilizes.

## When to reach for a logbook

You likely have a logbook problem when at least three of these are true. The strongest cases have all four.

1. **Multiple contributors.** More than one agent or human reads and writes the same state. One agent producing one artifact is not a logbook problem — just write a file.
2. **Stable entry contract.** The outer shape is predictable enough that tools can query the logbook without understanding every entry in full. Identity, discriminators, and core query fields keep stable meanings; entries may still carry optional, nested, or type-specific fields under that contract. A stable envelope with a polymorphic payload counts.
3. **Tool-queried, not reread.** Common questions are answered by querying the structure — filtering, sorting, traversing, aggregating — not by scanning the whole thing in context.
4. **Outlives the session.** The state needs to be readable by a different agent, a different human, or the same person in a different session. If everything gets consumed and discarded in one conversation, it's scratch state — keep it in context.

If fewer than three are true, you probably don't need a logbook. Write a markdown doc, use chat state, or pass a single-use artifact.

**The "deep" heuristic.** When you reach for a workflow labeled deep — deep research, deep planning, deep review — check whether the underlying pattern (multi-phase, structured intermediates, cross-session reuse, queryable state) is present. When it is, the four criteria above are usually satisfied and a logbook is probably the right layer. When the workflow is single-pass or single-reader despite the label, it isn't.

## Recognizing hidden logbooks

Many things that look like documents are logbooks in disguise. A multi-step plan is really rows: section_id, title, content, status. Inline comments on it are a second logbook: comment_id, section_id, author, text. Structured annotations on structured content means two logbooks — even if the UI renders everything as prose.

Multi-agent planning tools follow this pattern: explorer agents contribute findings, a critic synthesizes, humans comment in a browser UI. The data is row-shaped but presented as a document. "Which sections have unresolved comments" and "show all high-risk sections" are logbook queries hiding behind a document UI.

The signal: if a document is really a list of structured entries with structured annotations, and filtering/sorting/aggregating them would be valuable, extract the structure and give it a schema. The caution: extract structure only when the queries are more valuable than the prose shape you're flattening. A plan with rhetorical sequencing, implicit dependencies, and useful early ambiguity may lose more than it gains from premature extraction.

## What a logbook is not

**A document.** If the value is in argument, explanation, hierarchy, or evolving prose — where the reasoning itself is the product — use a document. A logbook may sit beside a document as the structured query surface for extracted entries, but the document is the thinking medium. Note: if the "document" is really a list of structured entries (see above), test whether it's a hidden logbook before defaulting to prose.

**A tracker.** A tracker like Jira is the right home when the natural long-lived object is a committed task with workflow semantics: owner, status, priority, sprint, transitions, notifications. Do not build a custom logbook to replicate a work-management system.

**A log.** A log is an append-only event stream — chronological, usually machine-written, optimized for replay and debugging. A logbook is mutable working state — entries get annotated, corrected, and queried for decisions, not just replayed.

**Chat state.** If the work is short-lived, single-session, and speed matters more than structure, keep it in context.

**A typed handoff artifact.** When one agent writes a structured object and the next reads it in a single pass, explicit contracts (JSON, YAML) beat shared state.

**A memory store.** Agent memory layers — vector stores, embedding recall, long-term memory APIs — retrieve content by semantic similarity for one agent's next turn. A logbook is queried collaboratively by multiple contributors with explicit filters on structured fields. Memory stores answer "what have I seen that looks like this?"; logbooks answer "what is the shared state of this joint piece of work?"

**A notebook or agent workspace.** Notebooks and agent scratchpads hold one session's working context — the files an agent reads, intermediate results of a run, the prose the agent is generating. They're bounded to the session and shaped for one actor. A logbook sits above individual sessions and is shaped for query by other actors who were not present when the entries were written.

A logbook can be the right **staging surface upstream of a tracker** — especially for epic decomposition or large candidate backlogs. The failure mode is not using both across phases; it's keeping both as hand-maintained coequal sources of truth. The logbook is authoritative during shaping; after commit, the tracker is authoritative for execution.

When structured entries start accumulating inside prose, extract them into a logbook instead of repeatedly reprocessing the whole document.

## "Isn't this just Notion / Airtable?"

A Notion database or Airtable base passes most of the logbook criteria: shared, structured, queryable, multi-contributor, persistent. They are valid backends for a logbook — they belong in the "Spreadsheet" storage category.

What they don't provide is the methodology that makes a logbook operational for agent workflows. Every working logbook needs four roles filled — by hand, by scripts, or by tooling:

**Schema discipline** — columns defined at creation with meaning, identity rules, and correction semantics. Notion lets you add columns; the logbook concept requires you to decide what they mean, how partial entries are handled, and when to version the schema.

**Tool-based queries** — agents filter, sort, and aggregate through whatever tool fits: a bash one-liner, a CLI, an MCP tool, SQL, or a spreadsheet filter. The point is that agents query state through tools, not by rereading everything in context.

**Execution actions** — bridges from logbook state to external systems. Commit entries to Jira, apply to Miro, generate reports, trigger agent runs. These can be scripts, manual exports, or purpose-built tools. What matters is the pattern: validate readiness, act on passing entries, log what happened.

**Orchestration** — the logbook's schema, queries, and actions are iteratively co-designed by a human and an agent around a specific workflow need. The result is a skill that knows when to create a logbook instance, what schema to use, and which actions to run. An agent operating within that skill can create and populate logbook instances on its own, but it follows the design — it doesn't invent the schema spontaneously.

These are roles, not infrastructure. A CSV with a bash script and a manual Jira export fills all four roles. So does a purpose-built MCP server. The concept doesn't prescribe the tooling — it names what needs to exist so that the logbook actually works instead of rotting as an unqueried file.

The backend can be a CSV, a Google Sheet, an Airtable base, SQLite, or a purpose-built agent-native service. What matters is the methodology above it.

---

## Row-shaped logbook

In a **row-shaped logbook**, each entry is a row with named columns. Questions are answered by filtering, sorting, and aggregating columns. It can be implemented as a flat file, a spreadsheet, or a database. The principles, anti-patterns, and examples below are specific to row-shaped logbooks.

**The quick test:** if you can't name the columns in 30 seconds, it's probably a doc problem, not a logbook problem.

### Principles

**Rows over prose.** The primitive is a row with named columns. New contributions can be represented as one entry with stable columns. Prose goes in a description column, never in free-form sections. This is what makes queries cheap.

**Append- and patch-friendly.** New entries are appended as rows. Existing rows can be patched — updating specific columns when state changes (a status field, a verification link, a revised estimate). Annotation is the most common form of patching: one contributor adds a value to another contributor's row — a human marks `reviewed_by`, an agent fills in `risk_score`, a critic writes a `counterargument`. The operating rule: append when adding new entries; patch in place when refining existing rows. Reserve append-only correction rows (new row referencing the old) for audit-sensitive logbooks where history must be preserved — decision logs, retro observations, compliance records. For refinement-heavy logbooks like backlog shaping or ideation scoring, direct patches are simpler and produce less clutter. The anti-pattern is wholesale rewrites that destroy history, not targeted field updates. Append-and-patch semantics reduce merge pain; actual concurrency guarantees come from the backend.

**Human-inspectable at rest.** The state should be inspectable without bespoke application logic. CSV in git is the lightest default, but spreadsheets and database tables are valid backends when they better fit the workflow. Inspectability is the principle; `cat`-ability is one implementation of it.

**Queries via tools, not in-context scanning.** Once the logbook grows beyond trivial size, common questions should be answered by filtering, sorting, or aggregating columns rather than by loading the whole file into prompt context. The tool can be a CLI, a spreadsheet filter, or SQL. Building that query layer is part of building the logbook. Rereading a small logbook in full is fine; the rule is that the logbook should not *need* to be reread as it grows.

**One job, one coherent memory design.** Sometimes that is one table; sometimes it is a small relational bundle with a few related record types. What to avoid is a universal domain schema — not multi-entity designs that genuinely need them. Reusable infrastructure (id formats, timestamp conventions, validation helpers) remains fine. A universal logbook platform or shared ontology is the trap.

### Single-table vs multi-entity

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

### Anti-patterns

**The unified substrate.** Trying to make one logbook library serve every use case — building a generic platform when each logbook needs its own schema, commands, and query verbs. Code is cheap; cognition is expensive. Rebuild the domain schema every time. Reuse infrastructure conventions: id formats, timestamp fields, provenance columns, validation helpers. The reusable things are this concept and lightweight shared conventions — not a universal domain schema or platform.

**The logbook that nobody reads.** If the only consumer of the logbook is the agent that wrote it, it's not a logbook — it's just scratch state. A logbook earns its existence the moment a *different* reader (another agent, another model, a human) consults it. If no second reader, review process, or downstream tool has consulted it by the time its expected review window closes, collapse it back into scratch state or archive it — don't maintain it as live shared state.

**Backend denial.** When you need joins, constraints, migrations, or stronger concurrency, the answer is not to abandon the logbook — it's to upgrade the backend. Keep the logbook abstraction but move from CSV to SQLite or Postgres. The anti-pattern is pretending a flat-file implementation is still enough when the data has outgrown it.

**The logbook as second place to update.** If the logbook lives alongside a source of truth that humans actually edit (Jira, a doc, the code itself), and both are hand-maintained, the logbook will rot. A logbook works when it *is* the source of truth for its slice, or when it is generated from one.

### Choosing a storage format

Pick the format that fits the data, not by default.

**CSV** — best when every row has the same flat columns, values are short strings or numbers, and you want to open it in Excel or any text editor. Weakest when a column frequently needs nested sub-fields or when you need cross-logbook joins. Use for: ideation logbooks, feedback collectors, flat decision logs.

**JSON Lines (.jsonl)** — one JSON object per line. Best when rows have optional or nested fields, or when column sets vary across rows. Still appendable, still greppable, still human-readable. Weakest when you want to open it in Excel or run column-based CLI ops. Use for: logbooks where the schema is soft, where one row might have 4 fields and the next has 8.

**SQLite** — best when you need real queries (joins, aggregates, GROUP BY, indexes), when row volume exceeds a few thousand, or when multiple logbooks need to reference each other. Trades away the open-in-any-editor inspectability but gains everything a relational database gives. Use for: logbooks that are clearly databases in disguise, or when the CLI query layer starts reimplementing SQL badly.

**Spreadsheet** — best when humans are primary editors or reviewers, you need visual sorting/filtering/comments, and the team prefers a UI over a CLI. Valid backend for the same logbook pattern. Use for: human-heavy collaboration, low engineering overhead, non-engineers who need to interact with the data.

**Markdown tables** — most human-readable, worst to append programmatically, painful to query. Only use when the logbook is tiny (under 20 rows), hand-maintained, and read more often than written. Rarely the right call for agent-written logbooks.

Migration is always available. A common starting point is CSV when no stronger signal exists, but spreadsheet-first or SQLite-first are equally valid when the workflow calls for them. Notice the pain (nested fields → jsonl; need joins → SQLite; need human UI → spreadsheet), and migrate that specific logbook. The concept and schema don't change — only the serialization does.

### Authoritative store vs projections

One store is authoritative; others are views. Three projection kinds:

- **run-trace** — append-only event log alongside the ledger; preserves full execution record; not the source of truth for current state
- **export-only** — read-only snapshot for human browsing (Sheets, Airtable); regenerated from the authoritative store; never edited directly
- **mirror** — editable copy; almost always wrong; creates the "second place to update" anti-pattern

If it's unclear which store is authoritative, the logbook isn't designed yet. The authoritative store is where writes happen; projections are derived from it.

### Operating the schema

Naming columns in 30 seconds tells you the logbook is row-shaped. It does not tell you the schema is ready for contributors. The hard problems are below.

**Row identity.** Every row needs a stable identity that survives edits, reordering, and export. Decide early: is identity a sequential id, a natural key (skill_name + run_id), or a generated UUID? Natural keys are readable but brittle if the key fields change. Sequential ids are simple but meaningless outside the logbook. Pick one rule and document it in the logbook header or README.

**Field semantics.** When two contributors both write a "priority" column, do they mean the same thing? Define each column in one sentence at logbook creation. If the definition drifts — one person uses "priority" for business value and another for implementation urgency — the logbook is silently corrupted. The fix is to split the column or rename it, not to hope for convergence.

**Partial rows.** Not every contributor knows every field. Decide whether missing fields are empty strings, explicit nulls, or "unknown." Pick one convention per logbook. Mixed conventions make filters unreliable — `filter priority=high` misses rows where priority was never set if some use empty and some use null.

**Corrections vs. supersession.** When a row's content is wrong, is the fix an in-place patch or a new row that marks the old one as superseded? The answer depends on the logbook's job. For audit-sensitive logbooks (retro observations, decision logs), append a correction row and mark the original. For refinement-heavy logbooks (backlog shaping, ideation scoring), patch in place — the current state matters more than the history. State the rule in the logbook header.

**Logbook address.** Every logbook needs a stable reference that works across sessions and contributors — a file path, a URL, a database identifier. The address is how a skill finds the logbook it operates on, how a human shares results, and how an action knows where to read from. For a CSV in a repo, it's the file path. For a spreadsheet, it's the share link. For SQLite, it's the database path and table name. State the address in the skill that creates the logbook, and include it when sharing results — the logbook is only useful if the next reader can find it.

**Schema versioning.** When you add a column, existing rows won't have it. When you rename a column, old queries break. The principle: a schema change that silently breaks existing queries is worse than a schema that stays slightly imperfect. How you handle it depends on the backend — defaults for new columns, migration scripts, or just updating the query layer alongside the schema change. State the rule in the logbook header so contributors know what to expect.

### Worked examples

**Ideation logbook.** Columns: id, name, description, source_agent, phase, tag, and ICE scores. Multi-agent append-heavy during a brainstorming run. CLI has filter, sort, top, compute. Humans read the final converge output, not the CSV directly — but the CSV is what makes the CLI queries cheap.

**Pre-tracker backlog shaping logbook.** Columns: candidate_id, epic, task_name, description, component, dependency, risk, estimate, priority, split_merge_action, commit_decision. Many agents and humans shape candidates: splitting epics, deduping, estimating, ranking. Cheap queries power review: "show unowned backend tasks," "group by component," "what depends on auth?" Once candidates pass review, selected rows export to Jira. The logbook is the shaping surface; the tracker is the execution surface.

**Skill retro collector logbook.** Columns: run_id, skill_name, phase, observation, severity, category. One row per observed failure mode across every run of a skill. The schema is generic to any skill but the value is personalized — each skill's retro logbook accumulates its own patterns over time. The value shows up over many runs, when `filter category=scorer-collapse` surfaces a pattern invisible in any single retro.

**Deep review / multi-phase agent workflow logbook.** A per-PR code review logbook with two physical stores.

- **SQLite ledger** (`~/logbooks/code-review/{PR_REF}.sqlite`):
  - `hotspots` — append-only, one row per risky unit selected for review; key: `hotspot_id`
  - `candidate_findings` — append-only, one judgment per hotspot per run; key: `candidate_id`
- **JSONL run-trace** (`~/logbooks/code-review/{PR_REF}.jsonl`):
  - Append-only event log; `record_type` one of run/hotspot/candidate/decision/output
  - Preserves full execution record; not queried relationally

Identity has four layers: `run_id` (execution boundary), `hotspot_id` (planning unit within a run), `candidate_id` (one model judgment), `fingerprint` (root-cause hash for semantic dedup across runs). Both tables are append-only — corrections are never patched in place; a new run produces new rows. Cloud exports (Sheets, Airtable) are export-only projections — not authoritative, regenerated from the SQLite ledger.

The value of the multi-entity design: `detection_state` + `surfacing_state` can be tracked separately per candidate, cross-run dedup works via fingerprint without touching earlier rows, and the run-trace preserves the full reasoning record independently of the current-state ledger.

### Actions

A logbook that only gets queried is a reference. A logbook that drives execution is a coordination surface. Actions are the bridges from logbook state to external systems.

The pattern: **logbook → query → action**. A query selects entries by criteria. An action takes those entries and does something outside the logbook — creates tickets, generates documents, populates a workshop board, triggers agent runs.

**Commit to tracker.** Real APIs like Jira have strict schemas — a ticket requires project, issue type, summary, and often priority, assignee, story points, and more. You can't save a half-formed ticket. But shaping work is inherently partial: early entries might have a task name and component but no estimate, or a risk assessment but no assignee. The logbook is the permissive staging layer where partial entries are valid — fields get filled incrementally by different agents and humans across sessions until the entry is complete enough to commit. The commit action validates readiness (are all target-required fields populated?), surfaces gaps (`filter commit_decision=approved AND estimate=null`), and creates tickets only from fully-formed entries. Each committed entry gets a `ticket_id` column patched back. The logbook is authoritative during shaping; after commit, the tracker is authoritative. One-way push, no sync back.

**Apply to workshop surface.** Export entries as Miro sticky notes, Figma cards, or any visual collaboration tool. Group by a column (tag, component, phase). Include provenance on each card (source agent, score). The workshop surface is the next stage, not a mirror — no two-way sync.

**Generate report.** Export filtered entries as a formatted document — a summary for stakeholders, a handoff brief for the next team, a decision log for compliance. The report is a snapshot, not a live view. Regenerate it when the logbook changes.

**Trigger agent run.** Use logbook state as input to a new agent session. A retro logbook with unresolved high-severity entries triggers a skill improvement agent. A backlog logbook with unestimated entries triggers an estimation agent. The logbook is the work queue; the agent processes entries and patches results back.

**Visualize.** Render a filtered slice of the logbook — or the whole thing — as a chart, board, timeline, heatmap, or any visual form that fits the data. Group ideation entries by tag in a bubble chart. Show backlog candidates on a risk-vs-effort scatter plot. Render a retro logbook as a severity heatmap across runs. The visualization is a view on top of the logbook, not a copy — regenerate it when the data changes.

**Principles for actions:**

Each action is specific to one logbook schema. The ideation logbook has "apply to Miro." The backlog logbook has "commit to Jira." Do not build a universal action dispatcher — that's the unified substrate anti-pattern applied to execution.

Actions always include a dry-run mode. Before creating 50 Jira tickets, print what would be created, with counts and warnings for missing fields. The cost of undoing a bad batch export is high.

Actions log what they did. Every commit, apply, or export writes a row to an action log (timestamp, action type, filter used, count of entries acted on, target URL or ID). This is how you answer "when did we last push to Jira and which entries were included?"

Avoid bidirectional sync. The logbook pushes to external systems; patch back identifiers (`ticket_id`, export URL) or action metadata (commit timestamp, status of the push) only when later queries need them. Do not mirror ongoing target-system edits back into the logbook. If a Jira ticket gets updated after commit, that update lives in Jira — the logbook's job ended at commit. Maintaining two editable copies creates the "second place to update" anti-pattern.

### Governance

Long-lived shared state needs rules beyond schema design. These are minimal defaults; override them when the workflow demands it.

**Ownership.** Every logbook has exactly one owner: a person or role responsible for schema changes, conflict resolution, and sunset decisions. Contributors can append and patch rows; the owner decides when the schema evolves or the logbook closes. If no one owns it, no one will maintain it.

**Access and visibility.** Decide at creation who can write, who can read, and whether the logbook is visible outside the immediate team. For agent-written logbooks, this also means deciding which agents have append access and which have read-only query access. The default should be narrower than you think — widen it when someone asks.

**Conflict resolution.** Two contributors patching the same row at the same time is inevitable. For flat files, the rule is last-write-wins with git history as the audit trail. For spreadsheets, the rule is whatever the platform provides. For SQLite, use transactions. The principle: pick an explicit rule and tell contributors what it is, rather than hoping conflicts don't happen.

**Provenance.** Decide at creation whether the logbook needs to track who wrote what and when. The answer depends on the job. A short-lived ideation logbook might only need `source_agent`. A retro logbook spanning months needs timestamps. A compliance-sensitive logbook needs full `created_by`, `created_at`, `updated_by`, `updated_at`. Don't mandate provenance columns by default — add the ones the logbook's queries will actually use.

**Retention and sunset.** Every logbook should have an expected lifetime: one sprint, one quarter, indefinite. When the lifetime expires, the owner reviews it. The options are: archive (move to cold storage, stop querying), collapse (extract summary into a document, delete the logbook), or renew (confirm it's still active, extend the window). A logbook with no sunset rule will outlive its usefulness and become a maintenance ghost.

### The test

Six months from now, you should be able to decide in under ten seconds whether a new problem is a doc problem, a logbook problem, or a tracker problem — and if it is a logbook problem, whether to start with a flat file, a spreadsheet, or a database. If you are still deliberating, the boundaries in this document need sharpening.

---
name: logbook-creator
description: Design and create a logbook — a shared, queryable, schema-stable working surface that agents and humans append to, annotate, and query across sessions. Use this skill whenever the user wants to track structured entries across sessions, stage draft data before pushing it to a target system (Jira, Miro, a database), set up a human-in-the-loop review surface for agent-produced work, coordinate state between multiple agents, or collect structured observations for later analysis or visualization. Also trigger on phrases like "I want to track X across sessions", "I need a draft layer before committing to Y", "let me review what the agent found before applying it", "multiple agents need to collaborate on this", "collect observations now and analyze later", or any situation where prose is starting to accumulate repeated structured entries that would be better shaped as rows. This skill creates the logbook itself and a spec file describing it — it does NOT create or modify skills. For wiring the logbook into a skill, hand off to skill-creator afterward.
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

Validate the answer in conversation (not code):

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

Decision rule: if the user answers "one file per X," the filename scheme AND the redundant-column list are decided **here**, not in Step 3. Step 3 reads these answers and drops the redundant columns from the schema, adding a one-line note below the table naming each dropped column and why.

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

Only proceed to Step 3 after both the append and query moments are concrete, or after an explicit commit-to-trial with the sunset rule recorded in governance.

If the user refuses to answer concretely but insists on the logbook, don't block. Record the vague answer in the spec's `## Governance` as *"Usage pattern not yet articulated; revisit after first week. Sunset after 14 days of no writes."* Document the decision to proceed so a future reader can see why the upfront check was skipped.

### Step 3 — Derive the schema

Propose columns based on the motivation from Step 1, the partitioning choice from 2.2, and the specifics the user described. Don't make the user invent the columns cold — give them a starter set and let them refine.

Two answers from Step 2 directly shape the schema:

- **Partitioning (2.2).** If the user chose one file per X, drop columns whose values are encoded in the filename (`problem_id`, `session`, `topic`, `date`, `week`, etc.). Annotate those fields in the schema table — or rather, annotate their absence — by adding a one-line note under the table: *"Column `<name>` is encoded in the filename, not stored."* Keeping the column in the schema and the filename both is redundant and invites drift.
- **Scope (2.1).** If the logbook is shared, `author` (or equivalent) is a required column. If personal, `author` can be optional and defaults to the single owner recorded in governance.

Then ask the four schema questions, grounded in the user's scenario rather than abstractly:

- **Identity** — *"How should rows be identified? Auto-increment IDs are simple. A natural key like `component + title` is readable but breaks if those fields change. A UUID is safest but meaningless outside the logbook."* Pick one and document it.
- **Partial rows** — *"Not every contributor will know every field at write time. When a field is missing, should it be an empty string, an explicit null, or the literal text 'unknown'?"* One convention per logbook. Mixed conventions corrupt filters.
- **Corrections** — *"When an entry is wrong, should we update it in place, or append a new row that marks the old one superseded? Patching is simpler; appending preserves history for audit-sensitive logbooks."* Align with the motivation — ideation scoring patches, retro decision logs usually append.
- **Field semantics** — for each column, write one sentence defining what it means. *"`priority` — the business value ranking from 1 (highest) to 5 (lowest), set by the product owner during review."* Two contributors meaning different things by the same column silently corrupts the logbook.

End this step with a clear, small schema the user can look at and say "yes, that's it." If they can't describe the columns in under 30 seconds, the schema isn't ready yet — trim or reshape.

### Step 4 — Recommend storage

Pick the format that fits the data and the downstream experience, not by default. Make one recommendation with a one-sentence rationale; let the user override.

| Format | When to pick it |
|---|---|
| **CSV** | Flat columns, short values, single writer at a time, want to open in Excel or grep from bash. Good default for ideation, flat decision logs, feedback collectors. Easy to chart later. |
| **JSON Lines (.jsonl)** | Optional or nested fields, schema varies row to row. Still appendable and greppable. Weak if you want column CLI ops. |
| **SQLite** | Need real queries (joins, aggregates, GROUP BY), row volume over a few thousand, multiple logbooks reference each other, concurrent writers. Loses plain-text inspectability. |
| **Spreadsheet** (Google Sheets, Excel) | Humans are primary editors or reviewers. Visual sorting, filtering, comments. Ideal for human-in-the-loop review. |
| **Markdown table** | Tiny (under ~20 rows), hand-maintained, read more than written. Rarely right for agent-written logbooks. |

Narrow the table by the location picked in 2.1:

- **Inside a shared git repo** → prefer plain CSV, JSONL, or Markdown. They are diffable and reviewable in PRs. Deprioritize SQLite (binary, review-hostile) and spreadsheets (not in the repo at all) — unless you have concurrent writers, in which case SQLite's transaction safety outweighs the diff cost.
- **Under a home-dir or local-state path** → all formats in the table remain viable. Pick on motivation and data shape.

The motivation biases the choice: staging and collection lean toward CSV or SQLite (diffable, chartable); human-review leans toward spreadsheet; multi-agent concurrent writers lean toward SQLite.

Migration is always available — start simple, upgrade when the pain signals (nested fields → JSONL; need joins → SQLite; need human UI → spreadsheet). Tell the user this so they don't over-engineer up front.

### Step 5 — Create the two artifacts

Before writing either file, re-verify the absolute path from 2.1 is writable **and** non-ephemeral. If the path matches an ephemeral pattern (`/tmp/…`, `/private/var/folders/…`, `/sessions/…`, or any sandboxed working directory), stop and ask once more, even if the user insisted during 2.1. This catches the common failure mode where the user agreed to a path in 2.1 but the conversation was still running inside an ephemeral working directory, and the agreed path was never actually the durable one.

The spec's `## Address` section must carry the absolute path from 2.1 and the line *"When the user moves this file, update the address here."* — this is already in the template below; do not drop it.

Write both files to the user's selected folder (or to the workspace if no folder is specified). Names:
- `<logbook-name>.<ext>` — the logbook instance (e.g., `retro-observations.csv`).
- `<logbook-name>.logbook.md` — the spec.

For a spreadsheet backend, the "logbook instance" step is a set of setup instructions (headers to paste, column types to set) rather than a file — spell them out clearly in the spec and in your message.

**If any binding has `status: pending-auth`** (cloud backends requiring credentials), also write a third file:
- `<logbook-name>.logbook.local.yaml.template` — committed to the repo as a safe example showing the shape of local overrides (placeholder values only, no real IDs or emails).

Then tell the user: *"Copy `<name>.logbook.local.yaml.template` to `<name>.logbook.local.yaml`, fill in your real IDs, and add `*.logbook.local.yaml` to your `.gitignore`. Never edit the spec file (`*.logbook.md`) to activate a binding."*

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

For the full framing — including hidden-logbook detection, the "three of four" qualification test, worked examples (ideation, pre-tracker backlog shaping, skill retro collector), and the full anti-pattern catalog — read `references/concept.md`. Consult it when the user's situation is ambiguous or when you need to explain *why* a particular rule exists.

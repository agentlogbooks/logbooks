---
name: generate.import
stage: generate
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - the user supplies their own ideas from an external source (pasted list, a file, notes, a meeting dump)
  - the intent is "import these", "here are my ideas", "store these", "log these ideas"
avoid_when:
  - the user wants the skill to generate ideas — use generate.brainstorm (plain) or generate.seed (persona)
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - evaluate.score
  - evaluate.taste_check
  - transform.refine
  - decide.compare
---

# Operator: generate.import

Ingest the user's OWN ideas from an external source and store them as first-class seeds.
No invention — this operator transcribes and normalizes; it does not add ideas of its own.
Because it is a `generate.*` operator, the orchestrator's Step 5B per-operator emit loop
auto-emits `idea_generated` for every imported row, so the wall populates at ingest with no
extra wiring — this is the whole point of importing through an operator rather than the raw CLI.

## Inputs

- `cohort_ids`: ignored — empty `[]`.
- `params`:
  - `source` (string, required) — the raw idea material exactly as the user supplied it:
    a pasted list, a block of notes, or a file path the orchestrator already read into the
    prompt. May be loosely structured (bullets, numbered, prose paragraphs).
  - `default_tag` (string, optional) — `SAFE`/`BOLD`/`WILD` to apply when an idea gives no
    temperature signal. Default: infer per idea; fall back to `BOLD`.

## Outputs

Writes to:
- `ideas` rows: one per distinct idea found in `source`, `kind=seed`, no lineage,
  `frame_id_at_birth` = the active frame (the planner guarantees one exists — see Reads).

## Reads

- Active frame (via `active-frame`). The orchestrator inserts a light placeholder frame
  (`frame.light`, the Light-frame precondition in SKILL.md Step 5B) BEFORE this operator so
  the not-null `frame_id_at_birth` FK resolves. This operator never creates or edits a frame
  itself (frames are touched only by `frame.*` and the orchestrator's `frame.light` insert).

## Prompt body

You are an idea importer. The user already has ideas; your job is to get them into the
logbook faithfully and cleanly — not to brainstorm new ones.

### Step 1 — Parse the source into discrete ideas

Read `params.source`. Split it into individual ideas. One bullet / line / numbered item /
short paragraph is usually one idea. When in doubt, keep the user's granularity — do not
merge two of their ideas into one, and do not split one into several. Preserve the user's
count.

### Step 2 — Normalize each idea (do NOT invent)

For each idea, produce:
- `title` — a short handle. Use the user's own words; if they gave only a description,
  derive a 3-6 word title from it.
- `description` — follow the **Description Writing Protocol** in `references/output-rules.md`
  (mechanism-first: state the concrete who-does-what in the first sentence; metaphor only as
  seasoning). Rewrite the user's idea into clean coffee-talk WITHOUT adding mechanism that
  isn't there. If the user's idea is vague, keep it faithfully vague — flag it in your return
  summary rather than inventing specifics. The reader test still applies, but fidelity to the
  user's intent outranks polish.
- `tag` — `SAFE`/`BOLD`/`WILD` from the idea's own temperature, else `params.default_tag`.

### Step 3 — Write the batch

Write all ideas in one `add-ideas-batch` call. Do not score, rank, or transform them — that
is the user's next move (offered as follow-ups), not part of import.

## Output discipline

- Follow `references/output-rules.md`.
- Faithfulness first: never add an idea the user didn't give, never drop one they did.
- Do not editorialize in the description ("great idea to…"); just state the idea.
- No methodology names in idea text.

## Commands

Read active frame (the planner ensured one exists):
```bash
python scripts/ideation_db.py active-frame $SLUG
```

Write the imported ideas:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG ideas.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: how many ideas were imported; the count the user supplied (confirm they match);
tag distribution; any ideas you flagged as too vague to state a concrete mechanism (so the
orchestrator can offer to develop them). One sentence, no scaffolding leaked.

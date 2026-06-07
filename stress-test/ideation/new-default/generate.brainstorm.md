---
name: generate.brainstorm
stage: generate
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - the lean default — a fresh topic, no ideas supplied, the user just wants ideas fast
  - one plain brainstorm pass, no persona, no technique, no framing ceremony
avoid_when:
  - the user supplied their own ideas — use generate.import
  - the user asked for the structured/technique treatment — use generate.seed personas (starter/deep_explore)
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

# Operator: generate.brainstorm

The lean default generator: ONE plain brainstorm pass over the whole problem, in a single
context, no specialist persona and no formal technique. This is the operator the
`plain-vs-starter` A/B validated (it beat the 2-persona `starter` default on substance,
relevance, and mechanism diversity, 4/4 blind judges) — ship THIS, not a repurposed
`generate.fresh`.

Why single-context matters (the measured edge): one agent sees its whole output, so it
naturally spreads across distinct mechanisms and won't emit near-duplicates. Two blind
parallel persona agents (the old default) cannot see each other and collide on the obvious
answers — the convergence Track A documented. The win here is **architectural**, not a claim
that personas/techniques are bad; the technique toolkit stays, on demand, on existing ideas.

## Inputs

- `cohort_ids`: ignored — empty `[]`.
- `params`:
  - `count` (int, default `12`) — target idea count in this one pass. (The A/B used 16; count
    is not load-bearing — the judges normalized to equal N.)

## Outputs

Writes to:
- `ideas` rows: `count` new rows, `kind=seed`, no lineage, `frame_id_at_birth` = the active
  frame (the planner ensures a light frame exists first for the FK).

## Reads

- Active frame (via `active-frame`) — used as light context (the problem statement), not as a
  technique scaffold. The lean default's frame is intentionally thin; real framing is on-demand.
- `facts` if any exist — cite at least one strong fact, same grounding rule as other generators.

## Prompt body

You are brainstorming ideas for a real problem in ONE pass. Read the active frame for the
problem statement, then brainstorm broadly and produce `count` varied, concrete ideas. Do NOT
use any formal technique, framework, persona, or framing exercise — just brainstorm well.

Because you can see your whole list as you write it:
- Make every idea a DISTINCT mechanism — no two should collapse to the same move. Scan your own
  list and replace any near-duplicate before returning.
- Spread across the problem's different root causes / angles; don't pile on the one obvious lever.
- Vary `tag` (`SAFE`/`BOLD`/`WILD`) across the set.
- Stay on the stated problem — a clever idea that doesn't actually move THIS problem is out.

## Output discipline

- Follow `references/output-rules.md`, including the **Description Writing Protocol**
  (mechanism-first; metaphor only as seasoning). Draft the mechanism internally, ship coffee-talk.
- Concrete example mandatory; no methodology names in idea text; no scaffolding leaked.

## Commands

```bash
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py add-ideas-batch $SLUG ideas.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: number of ideas written; tag distribution; a one-line note that mechanisms are
distinct (no near-duplicates); whether grounding was met if facts existed.

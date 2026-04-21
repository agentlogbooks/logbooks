# Operator: generate.fresh

Targeted seed generation to fill a specific gap the orchestrator or user has identified. No specialist persona — just the hint.

## Inputs

- `cohort_ids`: ignored — empty `[]`.
- `params`:
  - `hint` (string, required) — free-text direction, e.g. "more FIRE-zone ideas focused on in-store revenue", "seeds that address the trust root cause specifically", "ideas that work for solo founders with no budget".
  - `count` (int, default `6`) — target seed count. Keep this lean; `generate.fresh` is for filling a specific hole, not bulk generation.

## Outputs

Writes to:
- `ideas` rows: `count` new rows, `kind=seed`, no lineage.

## Reads

- Active frame (via `active-frame`).
- `facts` — citable context; same grounding rule as `generate.seed` (cite at least one strong fact if any exist).

## Prompt body

You are a seed generator called in to fill a specific gap. You are not wearing a persona — you are reading the hint, the active frame, and producing `count` seeds that directly address the hint while staying faithful to the frame.

### Step 1 — Read the frame and the hint

Read the active frame. Then read `params.hint`. Name in one sentence (internally) exactly what the hint is asking for — which root cause, which zone, which constraint, which stakeholder. If the hint is vague ("more ideas"), push back by generating with the broadest possible spread across the frame's root causes.

### Step 2 — Check grounding

If facts exist, cite at least one strong-confidence fact in at least one of the seeds produced. If the hint itself is grounded (mentions a specific competitor, benchmark, or documented failure), the citation can point at the fact that best matches it.

### Step 3 — Generate

Produce `count` seeds. Each:
- Addresses the hint specifically (if the hint says "in-store revenue", every seed should touch in-store revenue).
- Is grounded in at least one of the frame's root causes or HMW questions.
- Has a distinct mechanism — no two seeds in the batch should collapse to the same move.
- Carries a `tag` (`SAFE`/`BOLD`/`WILD`) chosen to match the hint's temperature (a hint like "ship this week, no budget" skews `SAFE`; "what would 10x look like" skews `WILD`).

## Output discipline

- Follow `references/output-rules.md`.
- Coffee-talk descriptions, concrete examples mandatory.
- Do not reference the hint itself in the description ("as requested by the user…"). The reader should never see the scaffolding.
- No methodology names in idea text.

## Commands

Read active frame + facts:
```bash
python scripts/ideation_db.py active-frame $SLUG
sqlite3 ./.ideation/$SLUG/logbook.sqlite \
  "SELECT fact_id, claim, confidence FROM facts ORDER BY confidence DESC;"
```

Write seeds:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG ideas.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: hint restated in one sentence; number of seeds written; tag distribution; which root cause each seed primarily addresses; whether grounding requirement was met.

---
name: evaluate.criteria
stage: evaluate
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - pool is ready for ranking but criteria are not yet locked
  - user asks to "score" or "prioritize"
avoid_when:
  - criteria already locked for this session
produces:
  ideas: false
  assessments: true
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - evaluate.score
---

# Operator: evaluate.criteria

Derive 5-7 session-specific evaluation criteria (with weights summing to 100) from the active frame and the cohort, then write them to a JSON side-car file. This operator does NOT score ideas — `evaluate.score` consumes the file it produces.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to consider when deriving session-specific criteria. The cohort should be large enough to reveal themes — typically all `status='active'` ideas.
- `params`: none required.
  - `include_universal` (bool, default true) — always include `feasibility` and `novelty` unless the frame explicitly rules them out.

## Outputs

- **External file:** `./.logbooks/ideation/$SLUG/criteria-$RUN_ID.json` — the criteria set and weights. Shape:
  ```json
  {
    "run_id": "<uuid>",
    "criteria": [
      {"name": "feasibility", "description": "...", "weight": 25},
      {"name": "novelty", "description": "...", "weight": 20},
      {"name": "trust_building_potential", "description": "...", "weight": 30},
      {"name": "scalability", "description": "...", "weight": 15},
      {"name": "engagement_depth", "description": "...", "weight": 10}
    ],
    "total_weight": 100
  }
  ```
- No logbook rows are written. Criteria live in the file; scoring runs reference it via the `criteria_path` param.

## Reads

- Active frame via `active-frame` (root causes + TRIZ contradiction drive session-specific criteria).
- Cohort ideas via `ideation_db.py ideas $SLUG --status active` and `ideation_db.py idea $SLUG $IDEA_ID`.
- Any prior `tension.*` assessments (`ideation_db.py assessments $SLUG --metric tension.*`) — tensions imply criteria (a `scale_vs_intimacy` tension suggests both `scalability` and `personalization` belong in the set).

## Prompt body

Derive criteria from THIS session, not a generic menu. The point is: two sessions on different problems should produce different criteria sets.

**Universal criteria (always unless the frame rules them out):**
- `feasibility` — "Can this be attempted soon with available resources?"
- `novelty` — "Does this open a direction competitors haven't explored?"

**Session-specific criteria (2-5, derived from the frame + tensions):**
- Each `root_cause` in the active frame suggests a criterion naming the thing the idea must address. Root cause "trust is inverting" → criterion `trust_building_potential`.
- Each `tension.*` axis in the cohort's assessments suggests a pair of criteria that together bridge the axis. Tension `scale_vs_intimacy` → include both `scalability` and `personalization` so an idea that scores high on both visibly resolves the tension.

**Rules:**
- 5-7 criteria total. Fewer → coarse ranking. More → weights become meaningless.
- At least 2 criteria must be session-specific (traceable to root causes or tensions).
- Weights are integers; must sum to exactly 100.
- Each criterion `name` is snake_case, a valid Python identifier, and matches the pattern used in `assessments.metric`.
- Write a one-sentence `description` per criterion that tells the downstream scorer what to look for. No jargon.

Write the file to `./.logbooks/ideation/$SLUG/criteria-$RUN_ID.json`. The path uses the session `run_id` (UUID). This ties the criteria to a specific session — a later `evaluate.score` call in a different session must derive its own criteria.

## Output discipline

- Follow `references/output-rules.md`. The file is machine-readable, but the `description` fields must remain coffee-talk — a human reviewing the criteria should instantly understand each.
- Do NOT score ideas here. Do NOT mutate any `ideas` rows. Do NOT write assessments.
- Do NOT invent criteria from a generic menu. At least 2 must trace directly to the active frame or to `tension.*` assessments in this session.

## Commands

```bash
# Read context
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py ideas $SLUG --status active
python scripts/ideation_db.py assessments $SLUG --metric-prefix tension.

# Write the criteria file
mkdir -p "./.logbooks/ideation/$SLUG"
cat > "./.logbooks/ideation/$SLUG/criteria-$RUN_ID.json" <<'JSON'
{
  "run_id": "$RUN_ID",
  "criteria": [
    {"name": "feasibility", "description": "Can this be attempted in the next quarter with existing resources?", "weight": 20},
    {"name": "novelty", "description": "Does this open a direction competitors haven't explored?", "weight": 15},
    {"name": "trust_building_potential", "description": "How directly does this address the frame's root cause that trust is inverting?", "weight": 30},
    {"name": "scalability", "description": "Can this reach every user without linear human effort?", "weight": 20},
    {"name": "personalization", "description": "Does each user feel the product understands their situation?", "weight": 15}
  ],
  "total_weight": 100
}
JSON
```

## Return

A 1-3 sentence outcome summary: which criteria were chosen and why each session-specific one exists (one-liner linking each to a root cause or tension), plus the absolute path of the file written so `evaluate.score` can find it.

---
name: evaluate.tension
stage: evaluate
scope: pool
applies_to:
  kinds: []
  min_cohort: 3
use_when:
  - the pool has multiple ideas and internal conflicts are not yet visible
  - you want to surface candidate pairs for hybridize
avoid_when:
  - pool has fewer than 3 ideas
produces:
  ideas: false
  assessments: true
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - transform.hybridize
  - transform.ratchet
---

# Operator: evaluate.tension

Find 3-5 structural contradictions among ideas in the cohort, produce a PMI per tension, and optionally write bridge ideas that honor both sides.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s in scope for tension analysis — typically the full shortlist or a cross-zone cohort.
- `params`:
  - `max_tensions` (int, default 5) — hard cap on tensions surfaced.
  - `write_bridges` (bool, default true) — if true, each tension may produce up to 2 bridge ideas.

## Outputs

- `assessments` rows — per tension:
  - One `metric=tension.<axis>` row on each of the two anchoring ideas. `value` is the truth that side sees (short phrase). `rationale` names both sides of the contradiction and cites the other idea's ID.
  - One `metric=tension_pmi.<axis>` row on each anchoring idea. `value` is one of `plus|minus|interesting`; `rationale` expands the PMI cell.
  - `<axis>` is a snake_case phrase derived from the contradiction (e.g. `tension.scale_vs_intimacy`, `tension.speed_vs_safety`). Use the same axis string across both sides of the same tension.
- `ideas` rows (optional): one `kind='variant'` bridge idea per resolved tension, linked to both parent ideas via `lineage` with `relation='derived_from'`.

## Reads

- Active frame via `active-frame` (especially `triz_contradiction` — the session's canonical trade-off).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Any prior `six_hats.*` assessments (a cohort evaluated by `evaluate.hats` first produces sharper tensions).

## Prompt body

Navigate the messy middle between generation and synthesis. The goal is structural contradictions — places where two ideas cannot both be maximally right at the same time. Do not surface surface-level disagreements ("one's mobile, one's web"); surface contradictions that reveal something about the problem.

**Step 1 — Find 3-5 tensions.** Look especially for cross-zone contradictions (a `FIRE`-tagged idea and an `ICE`-tagged idea pointing opposite directions on the same dimension is a structural tension). Name each tension with a short axis label like `scale_vs_intimacy` or `automation_vs_ownership`. For each tension, record what truth each side sees that the other isn't seeing.

**Step 2 — PMI on each tension.** For each of the 3-5 tensions, run Plus / Minus / Interesting. The "Interesting" column is where most breakthroughs hide — note what neither side has claimed but could.

**Step 3 — Bridge ideas (optional).** If a tension has a concrete resolution that honors both truths, write a bridge idea. The bridge must:
- Be a real combination, not a compromise. "Pick the middle" is not a bridge.
- Have both anchoring ideas as parents in `lineage`.
- Use coffee-talk description style — do not mention "tension" or methodology names.

**Step 4 — Check the frame.** If the active frame has a TRIZ contradiction (`triz_contradiction`), tag which cohort ideas resolve it, pick a side on it, or sidestep it. Record this as `metric=tension.frame_contradiction`, value one of `resolves|picks_side|sidesteps` on each cohort idea that's relevant.

## Output discipline

- Follow `references/output-rules.md`. Never name methodology (TRIZ / PMI / Groan Zone) in user-visible text.
- `rationale` cites the other idea by integer ID: "#47 says more personalization; this idea says less. #47 sees that trust comes from tailoring; this one sees that it comes from predictability."
- Bridge ideas must pass the coffee-talk rule — a concrete mechanism and a real-world example, no "combines #12 + #34" phrasing.
- Cap at `max_tensions`. Quality over count; skipping a weak tension is correct.

## Commands

**Batch every write.** For a cohort producing K tensions, this operator should produce exactly 1–2 write subprocess calls total (one `add-assessments-batch` for tension + tension_pmi + frame_contradiction rows, plus at most one `add-ideas-batch` if bridges are written), no matter how many tensions or bridges. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py ideas $SLUG --status active
python scripts/ideation_db.py idea $SLUG $IDEA_ID   # repeat per idea only when you need full detail

# Build ALL tension + PMI + frame_contradiction rows into one tempfile.
# For each tension: 2 tension.<axis> rows (one per anchor) + PMI rows for plus/minus/interesting on each anchor.
cat > /tmp/tension-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "tension.scale_vs_intimacy", "value": "scales via automation",
   "rationale": "#34 argues intimacy requires human touch; #12 sees that automation is the only path to reach every user. Both cannot be maximally true at the same time."},
  {"idea_id": 34, "metric": "tension.scale_vs_intimacy", "value": "intimacy via human touch",
   "rationale": "#12 argues scale demands automation; #34 sees that trust erodes without human presence. This is the session's deepest axis."},
  {"idea_id": 12, "metric": "tension_pmi.scale_vs_intimacy", "value": "plus",
   "rationale": "Automation reaches every user without headcount growth."},
  {"idea_id": 12, "metric": "tension_pmi.scale_vs_intimacy", "value": "minus",
   "rationale": "High-stakes requests feel robotic; trust erodes when users need a human."},
  {"idea_id": 12, "metric": "tension_pmi.scale_vs_intimacy", "value": "interesting",
   "rationale": "What if the AI layer handles predictable requests and escalates unpredictable ones to humans? Neither side has claimed this."},
  {"idea_id": 34, "metric": "tension_pmi.scale_vs_intimacy", "value": "plus",
   "rationale": "Trust is reinforced because a real person shows up at every critical step."},
  {"idea_id": 34, "metric": "tension_pmi.scale_vs_intimacy", "value": "minus",
   "rationale": "Can't grow past what your human ops team can personally touch."},
  {"idea_id": 34, "metric": "tension_pmi.scale_vs_intimacy", "value": "interesting",
   "rationale": "What if humans only appear when they're truly needed, and users see them as a premium signal?"},
  {"idea_id": 12, "metric": "tension.frame_contradiction", "value": "resolves",
   "rationale": "Directly cuts the automation/trust trade-off surfaced in the active frame."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/tension-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/tension-$OPERATOR_RUN_ID.json

# If any tensions produce bridge ideas, write them in ONE add-ideas-batch call with inline
# parents (so no separate lineage batch is needed).
cat > /tmp/tension-bridges-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"title": "Triaged-touch model",
   "description": "An AI router handles the predictable 80% of requests instantly; any message it flags as high-stakes goes to a human within 5 minutes. Users get speed on the easy stuff and real presence on the hard stuff.",
   "kind": "variant",
   "parents": [12, 34],
   "relation": "derived_from"}
]
JSON

python scripts/ideation_db.py add-ideas-batch $SLUG /tmp/tension-bridges-$OPERATOR_RUN_ID.json \
  --origin-operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/tension-bridges-$OPERATOR_RUN_ID.json
```

**Do not** call `add-assessment` or `add-idea` per row. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: number of tensions surfaced, which axes, bridge ideas produced (with IDs), and — if applicable — which idea was flagged as resolving the frame's TRIZ contradiction.

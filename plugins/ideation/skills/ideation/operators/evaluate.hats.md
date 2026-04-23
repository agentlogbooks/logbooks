---
name: evaluate.hats
stage: evaluate
scope: per_idea
applies_to:
  kinds: [seed, variant, hybrid, refinement]
  min_cohort: 1
use_when:
  - an idea wants a multi-perspective pass before deciding
  - emotional, data, and process angles are all missing
avoid_when:
  - already hat-evaluated recently on this lineage
produces:
  ideas: false
  assessments: true
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 1
followups:
  - transform.refine
  - decide.compare
---

# Operator: evaluate.hats

Run a six-hats evaluation on each idea in the cohort, persist one assessment per hat, and surface any bridge ideas the Green hat generates.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to evaluate (typically top-N by composite or a themed cohort).
- `params`:
  - `max_ideas` (int, default 10) — safety cap; if the cohort exceeds this, evaluate the first `max_ideas` in order.

## Outputs

- `assessments` rows: 6 rows per idea — metrics `six_hats.white`, `six_hats.red`, `six_hats.black`, `six_hats.yellow`, `six_hats.green`, `six_hats.blue`. `value` is a short phrase (e.g. `exciting`, `smooth`, `blocker`); `rationale` carries the one-liner for that hat.
- `ideas` rows (optional): one `kind='variant'` bridge idea per Green-hat combination suggestion that crosses the cohort; linked via `lineage` to its parent(s) with `relation='derived_from'`.
- No external files.

## Reads

- Active frame via `active-frame` (for root causes + tensions context).
- Each cohort idea row via `ideation_db.py idea $SLUG $IDEA_ID`.
- Prior assessments for the cohort (to avoid duplicating recent hat verdicts within the same run).

## Prompt body

For each idea in `cohort_ids`, apply all six hats. Breadth over depth — one crisp bullet per hat is the target. Do not turn this into a full analysis; downstream tension / scoring operators do the heavy lift.

**White (facts):** What data supports this idea? What contradicts it? What are we assuming?

**Red (gut):** How does it feel? Exciting, scary, boring, energizing? No justification — pure instinct.

**Black (risk):** What could go wrong? Hidden costs, unintended consequences? Do NOT use Black to kill the idea — use it to mark invert candidates (whether the risk should trigger a later `transform.invert`).

**Yellow (upside):** Best case scenario? Who benefits most? What's the ceiling?

**Green (alternatives):** What variations exist? What other cohort ideas would combine well with this one? If a cross-cohort combination is concrete enough to describe in a sentence, append a bridge idea (see below).

**Blue (process):** Does this fit the active frame's root causes and constraints? Smooth / friction / blocker?

**Bridge ideas.** If Green produces a specific combination of two cohort ideas that would be stronger than either alone, add it as a new `kind='variant'` idea with both parents linked via `lineage` (`relation='derived_from'`). Write the description in coffee-talk style — no "Green Hat combined #12 + #34" phrasing in the prose; just describe the mechanism and its impact.

## Output discipline

- Follow `references/output-rules.md`. Never name "Six Thinking Hats" or individual hats in user-visible prose — the hat namespace lives in `metric` only. The `rationale` field describes the observation; it does not mention the methodology.
- Do not include scores or weights in hat verdicts. `value` is an enum-like phrase; `rationale` is qualitative.
- Cap bridge ideas at 3 per run — if Green suggests more, pick the strongest. Each bridge must pass the coffee-talk description rule.

## Commands

**Batch every write.** For a cohort of N, this operator should produce exactly 1–2 write subprocess calls total (one `add-assessments-batch` for the 6×N hat rows, plus at most one `add-ideas-batch` if Green surfaces bridge ideas), no matter how many ideas you evaluate. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py ideas $SLUG --status active
python scripts/ideation_db.py idea $SLUG $IDEA_ID   # repeat per idea only when you need full detail

# Build ALL 6×N hat assessments into one tempfile.
cat > /tmp/hats-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "six_hats.white", "value": "supports: strong",
   "rationale": "Customer interviews in the active frame already confirm the pain point this idea addresses."},
  {"idea_id": 12, "metric": "six_hats.red", "value": "exciting",
   "rationale": "Team lights up at the demo; the mechanism feels inevitable."},
  {"idea_id": 12, "metric": "six_hats.black", "value": "regulatory_risk",
   "rationale": "Data-residency rules in the EU could force a second deployment — invert candidate."},
  {"idea_id": 12, "metric": "six_hats.yellow", "value": "ceiling_high",
   "rationale": "If the pricing ratchet holds, ARR compounds with every new segment."},
  {"idea_id": 12, "metric": "six_hats.green", "value": "combines_with_34",
   "rationale": "Paired-signal onboarding: fuses #12's cold-start cut with #34's empty-state fix."},
  {"idea_id": 12, "metric": "six_hats.blue", "value": "smooth",
   "rationale": "Aligns with the root cause in the active frame; no constraint conflict."},
  {"idea_id": 13, "metric": "six_hats.white", "value": "supports: medium",
   "rationale": "One interview supports; no quantitative backing yet."},
  {"idea_id": 13, "metric": "six_hats.red", "value": "flat",
   "rationale": "Neither excites nor worries; feels safe."}
]
JSON

# ONE call writes all 6×N hat rows.
python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/hats-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/hats-$OPERATOR_RUN_ID.json

# If Green surfaces up to 3 bridge ideas, write them in ONE add-ideas-batch call with
# inline parents (so no separate lineage batch is needed).
cat > /tmp/hats-bridges-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"title": "Paired-signal onboarding",
   "description": "Users see a one-minute welcome tour AND their team's current workspace pre-loaded. You cut the cold-start friction of #12 and the empty-state confusion of #34 in one step.",
   "kind": "variant",
   "parents": [12, 34],
   "relation": "derived_from"}
]
JSON

python scripts/ideation_db.py add-ideas-batch $SLUG /tmp/hats-bridges-$OPERATOR_RUN_ID.json \
  --origin-operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/hats-bridges-$OPERATOR_RUN_ID.json
```

**Do not** loop over ideas calling `add-assessment` six times each. The batch form is strictly faster and preserves transactional atomicity — either every hat lands or none do.

## Return

A 1-3 sentence outcome summary: number of ideas evaluated, total hat assessments written, any bridge ideas generated (with IDs), and any cohort ideas skipped (e.g. already hat-evaluated in this run).

---
name: transform.invert
stage: transform
scope: per_idea
applies_to:
  kinds: [seed, variant, hybrid]
  min_cohort: 1
use_when:
  - promising but brittle
  - obvious objections or failure modes
  - assumptions look too cautious
avoid_when:
  - already inverted recently on this lineage
  - idea too vague to invert meaningfully
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 1
followups:
  - transform.refine
  - validate.proof_search
---

# Operator: transform.invert

Reverse brainstorming on a cohort: for each idea, enumerate ways it could fail, then flip each failure into an improvement.

## Inputs

- `cohort_ids`: 1+ ideas. Typically seeds or early variants that look promising but untested.
- `params`:
  - `failures_per_parent` (int, default `4`) — target number of failure modes to generate per cohort idea; 3–5 is the sweet spot.
  - `min_flips` (int, default `2`) — minimum number of failure modes that must produce a child variant. Not every failure has to flip into a usable idea.

## Outputs

Writes to:
- `ideas` rows: `kind=variant`, one per successful failure→fix flip. Tag usually moves one step toward `BOLD` because inversions attack the safest assumptions.
- `lineage` rows: one per child, `relation=derived_from`, pointing at the single parent idea.

## Reads

- Active frame (to keep flips honest against the actual problem).
- Each cohort idea (via `idea $SLUG $ID`).

## Prompt body

You are the Inverter. Most people, asked "how do we succeed?", produce cautious, pre-filtered ideas. The trick is to flip the question: **"how could this guarantee failure?"** — and suddenly everyone is specific, creative, and honest. The failure modes you collect aren't jokes; they're an inventory of how the idea actually resists being real. Each inverted into its underlying principle is a new seed.

### Process per parent idea

1. **Restate the parent in one sentence.** Anchor the inversion in the real idea, not a strawman.
2. **Enumerate `failures_per_parent` failure modes.** Aim for *absurd AND specific*. "Users must solve a captcha while standing on one foot" beats "bad UX." "We launch the day of a major competitor's press release" beats "bad timing." Polite failures produce polite (useless) seeds.
3. **Invert each failure — do not just negate it.** If the failure is "we hide the price until checkout", the inversion is not "show the price"; it's the principle underneath: "radical transparency about cost at every touchpoint."
4. **Produce a child variant per usable flip.** At least `min_flips` per parent. If an inversion doesn't produce anything stronger than the parent, skip it — do not write weak children just to hit a quota.

### Tag choice

Inversions tend to surface hidden assumptions, so tags skew `BOLD` or `WILD`. If a flip lands clearly `SAFE` (most common fixes), keep the `SAFE` tag — we don't inflate.

### Watch out for

- **Symmetric pairs.** If the failure and its flipped seed are photo-negatives ("fast" ↔ "slow"), you haven't abstracted the mechanism. Find the principle underneath the failure.
- **Polite failures.** "A little slow" is a non-failure. Push to "crashes every third click during checkout." Embarrassing failures produce good seeds.
- **Filtering at generation.** Speed and honesty over polish. Triage happens later.

## Output discipline

- Follow `references/output-rules.md`.
- When writing descriptions, follow the **Description Writing Protocol** in `references/output-rules.md` — draft the mechanism internally, then rewrite as coffee-talk. The draft does not ship.
- Descriptions are coffee-talk prose — never narrate the flip ("I took the failure 'slow onboarding' and inverted it to…"). Just state the resulting idea with a concrete example.
- No methodology name in user-facing text. No "inversion" or "reverse brainstorming" in titles or descriptions.
- Each child has exactly one parent with `relation=derived_from`.

## Commands

Read each cohort idea:
```bash
python scripts/ideation_db.py idea $SLUG $IDEA_ID
```

Write children with inline lineage:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG children.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

```json
[
  {
    "title": "Radical cost transparency",
    "description": "Every page shows the total you'll pay before you click — including the fees competitors hide until checkout. A shopper comparing plans sees the real number, not the headline price, and either bounces fast or commits with confidence.",
    "kind": "variant",
    "tag": "BOLD",
    "parents": [23],
    "relation": "derived_from"
  }
]
```

## Return

Report: cohort size; failures enumerated per parent (average); children written; parents where no flip produced a usable variant (with the most interesting failure mode they still surfaced, even if not promoted).

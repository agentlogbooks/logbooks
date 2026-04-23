---
name: transform.hybridize
stage: transform
scope: group
applies_to:
  kinds: [seed, variant, hybrid]
  min_cohort: 2
use_when:
  - two or three ideas have complementary mechanisms
  - a tension cluster wants synthesis
  - FIRE and ICE ideas could combine ambition with ship-ability
avoid_when:
  - only one idea in the cohort
  - candidates are near-duplicates (hybridizing adds nothing)
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 2
followups:
  - transform.refine
  - validate.proof_search
---

# Operator: transform.hybridize

Merge two or more cohort ideas into a child that is stronger than any parent alone. Multi-parent lineage.

## Inputs

- `cohort_ids`: 2+ ideas. Typical cohort: a shortlist, a tension cluster, or a cross-zone pair. The operator treats the cohort as a pool and picks the most generative 2- or 3-idea subsets.
- `params`:
  - `hybrids_count` (int, default `3`) — target number of hybrid children to produce across the cohort. Keep it small — a hybrid that takes the best of two parents is more valuable than five mediocre blends.
  - `max_parents_per_hybrid` (int, default `3`) — hard cap. Four-parent hybrids usually collapse into mush.

## Outputs

Writes to:
- `ideas` rows: `kind=hybrid`. Tag usually `BOLD`; occasionally `WILD` when the blend is unexpected.
- `lineage` rows: one per (child, parent) pair, `relation=hybrid_of`. A 2-parent hybrid produces 2 lineage rows; a 3-parent produces 3.

## Reads

- Active frame — to check the hybrid still addresses the problem.
- Each cohort idea.

## Prompt body

You are the Synthesizer for this operator. The best hybrids are not "a bit of both" compromises — they are new structures that satisfy constraints from each parent simultaneously, often producing something neither parent could have reached alone.

### Process

1. **Read the cohort.** Line up every cohort idea's title + description + tag + zone (if set). Look for parents that:
   - Address different root causes (hybrid covers more ground)
   - Come from different temperature zones (FIRE+ICE hybrids are especially strong — they pair ambition with ship-ability)
   - Stand in tension with each other (contradictions are the richest source of hybrids)
2. **Pick the best subsets.** For each planned hybrid, pick 2 or 3 parents whose combination produces a mechanism greater than the sum. Do not hybridize every possible pair — hybridize where it is generative.
3. **Draft the hybrid.** The child description must make it obvious what each parent contributed, in plain language — but without naming parent titles or ideas ("Idea #7 contributed…"). The reader sees a clean idea, not a merger memo.
4. **Test the hybrid against the parents.** A hybrid that just averages is weaker than either parent alone — reject it. A hybrid that picks a side is a `transform.refine` on one parent — not a hybrid. A true hybrid introduces a new structure (often a mechanism from one parent applied under a constraint from the other) that resolves the tension.

### Watch out for

- **Compromise masquerading as synthesis.** "Half proactive, half reactive" is not a hybrid. Real hybrids have a new mechanism.
- **Mush.** Four-parent blends are almost always incoherent. Stay at 2–3.
- **Forced pairs.** Not every cohort idea wants a partner. If no strong blend is visible, write fewer hybrids.

## Output discipline

- Follow `references/output-rules.md`.
- When writing descriptions, follow the **Description Writing Protocol** in `references/output-rules.md` — draft the mechanism internally, then rewrite as coffee-talk. The draft does not ship.
- Coffee-talk description; concrete example mandatory.
- No reference to "hybrid" as a method or to parent idea IDs in user-facing text.
- Every parent of every child must have its own lineage edge (one edge per parent).
- `kind=hybrid` is correct only when 2+ parents are genuinely combined. If a child turns out to have one real parent and one decorative one, drop the decorative parent and make it a `transform.refine` on the real one.

## Commands

Read cohort ideas:
```bash
for IDEA_ID in "${COHORT_IDS[@]}"; do
  python scripts/ideation_db.py idea $SLUG $IDEA_ID
done
```

Write hybrids with inline multi-parent lineage:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG children.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

```json
[
  {
    "title": "Streak-only loyalty",
    "description": "A single daily streak replaces the whole loyalty tier system — one counter, one action, one reward for consistency. It keeps the 'one-click daily habit' idea's gentleness but borrows the streak mechanic from the wilder gamification proposal, so it ships next week without the leaderboards-and-badges overhead.",
    "kind": "hybrid",
    "tag": "BOLD",
    "parents": [52, 71],
    "relation": "hybrid_of"
  }
]
```

Alternatively, write child then lineage edges separately:
```bash
python scripts/ideation_db.py add-idea $SLUG \
  --title "..." --description "..." --kind hybrid --tag BOLD \
  --origin-operator-run-id $OPERATOR_RUN_ID
# Then one add-lineage per parent:
python scripts/ideation_db.py add-lineage $SLUG \
  --child $CHILD --parent 52 --relation hybrid_of \
  --operator-run-id $OPERATOR_RUN_ID
python scripts/ideation_db.py add-lineage $SLUG \
  --child $CHILD --parent 71 --relation hybrid_of \
  --operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: cohort size; hybrids written (count and parent arities); tag distribution; any candidate pair considered but rejected as compromise-not-synthesis (with a one-sentence reason).

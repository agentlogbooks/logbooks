# Operator: decide.shortlist

Promote the top-N cohort ideas to `status='shortlisted'` and record a one-sentence reason per promoted idea.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s that are candidates for shortlisting. Typically the output of the `top-by-composite` cohort query or a themed cohort.
- `params`:
  - `n` (int, default 5) — number of ideas to shortlist. Must be ≤ `len(cohort_ids)`.

## Outputs

- `ideas` mutable-field patches: `status='shortlisted'` on the top-N by `score_summary` within the cohort. Ideas not promoted stay at `status='active'`.
- `assessments` rows: one per promoted idea, `metric=shortlist_reason`, `value` = short phrase (e.g. `highest_composite_in_cohort`, `bridges_top_tension`, `brilliant_tier`). `rationale` = one sentence justifying the shortlist decision.

## Reads

- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID` (for `score_summary`, `evidence_state`, `tag`).
- Prior `brilliance.tier` and `web_stress_verdict` assessments — these can override raw `score_summary` when picking the top N.

## Prompt body

**Step 1 — Rank the cohort.** Default sort is `score_summary DESC`. If `score_summary` is NULL for any cohort idea, rank those last (no composite = no discrimination).

**Step 2 — Adjust for non-score signals:**
- An idea with `brilliance.tier='brilliant'` jumps above its raw-composite rank — "brilliant + middling composite" beats "high composite + not brilliant" for a shortlist.
- An idea with `evidence_state='disputed'` drops below its raw-composite rank — a refuted idea does not belong on a shortlist unless the user explicitly re-enables it.

**Step 3 — Pick the top N.** If two ideas are tied on adjusted rank, prefer the one with a higher `brilliance` yes-count, then the one with lower `idea_id` (deterministic tiebreak).

**Step 4 — Patch status and record reason.** For each of the N promoted ideas:
- Patch `status='shortlisted'`.
- Write a `shortlist_reason` assessment: `value` is a compact label; `rationale` is one sentence — what makes this idea deserve a shortlist slot. Examples:
  - "Highest composite in cohort; survived all web-stress rounds."
  - "Tier-2 composite but BRILLIANT rating — the one-mechanism insight is load-bearing."
  - "Bridges the session's deepest tension per #47 ↔ #58."

## Output discipline

- Follow `references/output-rules.md`. No raw scores in the rationale. "Highest composite" is OK; "composite 7.6" is not.
- Never demote — if an idea is currently `status='selected'`, skip it (the converge operator owns that terminal state).
- Never touch `status='rejected'` ideas. If a rejected idea appears in `cohort_ids`, skip it and note the skip in the return summary.

## Commands

**Batch every write.** For N promoted ideas, this operator should produce exactly 2 write subprocess calls total — one `patch-ideas-batch` (all `status='shortlisted'` patches) and one `add-assessments-batch` (all `shortlist_reason` rows) — no matter how many ideas are promoted. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Rank (per-row reads are fine)
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py latest-assessment $SLUG --idea-id $IDEA_ID --metric brilliance.tier
python scripts/ideation_db.py latest-assessment $SLUG --idea-id $IDEA_ID --metric web_stress_verdict

# Patch status='shortlisted' for ALL promoted ideas in ONE call.
cat > /tmp/shortlist-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "column": "status", "value": "shortlisted"},
  {"idea_id": 34, "column": "status", "value": "shortlisted"},
  {"idea_id": 47, "column": "status", "value": "shortlisted"},
  {"idea_id": 58, "column": "status", "value": "shortlisted"},
  {"idea_id": 71, "column": "status", "value": "shortlisted"}
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/shortlist-patch-$OPERATOR_RUN_ID.json

rm -f /tmp/shortlist-patch-$OPERATOR_RUN_ID.json

# Write ALL shortlist_reason assessments in ONE call (one per promoted idea).
cat > /tmp/shortlist-reasons-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "shortlist_reason", "value": "highest_composite",
   "rationale": "Highest composite in cohort; survived both web-stress rounds cleanly."},
  {"idea_id": 34, "metric": "shortlist_reason", "value": "brilliant_tier",
   "rationale": "Tier-2 composite but BRILLIANT rating — the one-mechanism insight is load-bearing."},
  {"idea_id": 47, "metric": "shortlist_reason", "value": "bridges_top_tension",
   "rationale": "Bridges the session's deepest tension per #47 ↔ #58."},
  {"idea_id": 58, "metric": "shortlist_reason", "value": "strong_evidence",
   "rationale": "Web-stress verdict is survives_scrutiny with three supporting facts."},
  {"idea_id": 71, "metric": "shortlist_reason", "value": "user_picked",
   "rationale": "User picked in taste check; composite is solid if not top."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/shortlist-reasons-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/shortlist-reasons-$OPERATOR_RUN_ID.json
```

**Do not** call `patch-idea` or `add-assessment` per row. The batch form is strictly faster and preserves transactional atomicity — either every promotion lands or none do.

## Return

A 1-3 sentence outcome summary: list of promoted IDs, any ideas skipped (with reason — `rejected`, `selected`, or NULL `score_summary`), and whether a brilliance-based override changed the shortlist vs. raw composite rank.

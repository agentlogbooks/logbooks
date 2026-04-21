# Operator: transform.ratchet

Resolve a tension cluster through structured thesis → antithesis → synthesis cycles. Every cycle locks constraints from the prior one; the ratchet only moves forward.

## Inputs

- `cohort_ids`: 2+ ideas that stand in tension (typically populated by a `tension_cluster` cohort query, or a pair picked explicitly by the orchestrator). Minimum: one pair of contradicting ideas.
- `params`:
  - `cycles` (int, default `2`) — how many thesis/antithesis/synthesis cycles to run. Valid range 1–3. Use 1 for a quick pass, 2 for standard, 3 when the contradiction is deep and deserves full TRIZ principle application.
  - `zone` (string, optional) — tag the output idea's `temperature_zone` with this zone (e.g. `PLASMA` for structural syntheses, `FIRE` for wild ones). If absent, leave the zone NULL.

## Outputs

Writes to:
- `ideas` rows: one synthesis idea per tension resolved. `kind=hybrid` if it merges parents into a new structure; `kind=variant` if it emerges from a single side with the constraints of the other baked in.
- `lineage` rows: `relation=hybrid_of` for each parent when the resolution is a genuine merge; `relation=derived_from` to the surviving parent when the ratchet flags the contradiction as unresolved and passes a weaker synthesis forward.
- `assessments` rows (optional): `metric='tension.ratchet_status'`, `value` in `resolves`/`partially_resolves`/`unresolved`, with a rationale naming the locked constraints.

## Reads

- Active frame — especially the TRIZ trade-off.
- Each cohort idea.

## Prompt body

You are the Dialectical Ratchet. You resolve contradictions through structured cycles. You are not a mediator — you are a synthesis engine.

### The ratchet rules

- Once a constraint is **locked**, it cannot be violated in subsequent cycles.
- Constraints are cumulative — each cycle adds; none removes.
- If a synthesis attempt violates a locked constraint, reject it and try again.
- The ratchet only moves forward.

### Per cycle

**Cycle 1: First clash**
1. **THESIS.** Take the strongest idea from Side A. State it fully.
2. **ANTITHESIS.** Take the strongest idea from Side B. State it fully.
3. **SYNTHESIS ATTEMPT.** Try to create an idea that satisfies both sides simultaneously — a new structure, not a compromise.
4. **EVALUATE.** Is this genuine synthesis or compromise?
   - Compromise ("a bit of both") → mark **WEAK**, continue to Cycle 2.
   - Synthesis ("a new structure that honors both truths") → mark **STRONG**.
5. **LOCK.** Extract what's TRUE from each side. These become locked constraints for every later cycle. Write them down as "From thesis: [insight]" / "From antithesis: [insight]".
6. **TRIZ HINT.** Which TRIZ inventive principle could break the deadlock? (Segmentation, Taking Out, Nesting, Prior Action, Dynamization, Another Dimension, Feedback, Self-Service, Inversion, Cheap Short-Life, Parameter Changes are common business-relevant picks.) Use it to drive the next cycle's synthesis attempt.

**Cycle 2: Refined clash**
1. **THESIS.** The Cycle 1 synthesis (or the stronger side if synthesis was weak).
2. **ANTITHESIS.** Must find a NEW objection. Cannot repeat Cycle 1's antithesis — the antithesis evolves as the thesis improves.
3. **SYNTHESIS ATTEMPT.** Must respect all locked constraints from Cycle 1.
4. **EVALUATE + LOCK + TRIZ HINT** — same as Cycle 1.

**Cycle 3 (only if `cycles=3`): Resolution**
Same structure. All prior locks still enforced. If the synthesis is still WEAK after Cycle 3, flag it as **UNRESOLVED** and write an assessment so a later operator (or the user) can decide whether to carry both sides forward.

### Quality check before writing the child

- All locked constraints satisfied?
- Synthesis is genuinely new, not "a bit of both"?
- TRIZ contradiction addressed, not sidestepped?
- A reader from Side A would accept this?
- A reader from Side B would accept this?

If any check fails, either run one more cycle (up to the `cycles` cap) or flag as UNRESOLVED.

### Watch out for

- **Compromise masquerading as synthesis.** "Half proactive, half reactive" is not a synthesis.
- **Dropped locks.** The whole point is cumulative pressure. A later cycle that quietly relaxes an earlier lock is not a ratchet — it's a regression.
- **Repeating antitheses.** If Cycle 2's antithesis is Cycle 1's rephrased, the debate hasn't evolved. Force a new objection.
- **Forcing resolution.** Some contradictions are genuine. If 3 cycles don't resolve it, flag UNRESOLVED — a fake synthesis is worse than an honest impasse.
- **Generating from scratch.** The ratchet synthesizes from what is on the table. It does not invent new parents.

## Output discipline

- Follow `references/output-rules.md`.
- When writing descriptions, follow the **Description Writing Protocol** in `references/output-rules.md` — draft the mechanism internally, then rewrite as coffee-talk. The draft does not ship.
- The user-facing description tells the resulting idea with a concrete example. It does not narrate "thesis / antithesis / synthesis" or name TRIZ principles. The ratchet is internal.
- Record the ratchet audit (cycle count, locked constraints, TRIZ hint used, status) as an assessment so the history is queryable without polluting the idea description.

## Commands

**Batch every write.** For a run producing N synthesis children, this operator should produce exactly 1–2 write subprocess calls total — one `add-ideas-batch` (inline parents carry lineage in the same call) plus, optionally, one `add-assessments-batch` for the ratchet audit rows. No matter how many pairs are ratcheted. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read cohort and active frame (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
for IDEA_ID in "${COHORT_IDS[@]}"; do
  python scripts/ideation_db.py idea $SLUG $IDEA_ID
done
```

Write ALL synthesis children in ONE `add-ideas-batch` call. Inline `parents` handles the
lineage edges in the same transaction — no separate `add-lineage-batch` is needed. Use
`relation="hybrid_of"` when the resolution is a genuine merge, `relation="derived_from"`
when the ratchet flagged the contradiction as unresolved and forwarded a weaker synthesis.

```bash
cat > /tmp/ratchet-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"title": "Triaged-touch pricing",
   "description": "The pricing page shows a flat rate but every booking flags stakes; high-stakes bookings route to a human reviewer before the rate locks. Speed for the simple case, human presence where it counts.",
   "kind": "hybrid", "tag": "BOLD", "zone": "PLASMA",
   "parents": [18, 29], "relation": "hybrid_of"},
  {"title": "Weekly review rollover",
   "description": "If the pricing decision wasn't resolved by Friday, it carries the prior week's rate and surfaces the unresolved objection at Monday standup. Prevents stuck deals without forcing fake synthesis.",
   "kind": "variant", "tag": "SAFE", "zone": "PLASMA",
   "parents": [18], "relation": "derived_from"}
]
JSON

python scripts/ideation_db.py add-ideas-batch $SLUG /tmp/ratchet-$OPERATOR_RUN_ID.json \
  --origin-operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/ratchet-$OPERATOR_RUN_ID.json
```

Record the ratchet audit for every child in ONE `add-assessments-batch` call:

```bash
cat > /tmp/ratchet-audit-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 91, "metric": "tension.ratchet_status", "value": "resolves",
   "rationale": "Locked: flat-rate transparency, human escalation path, no mid-week price change. TRIZ principle applied: Segmentation."},
  {"idea_id": 92, "metric": "tension.ratchet_status", "value": "unresolved",
   "rationale": "Locked: weekly cadence only. Contradiction forwarded; a later operator or the user should decide."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/ratchet-audit-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/ratchet-audit-$OPERATOR_RUN_ID.json
```

**Do not** call `add-idea` or `add-assessment` per row. The batch form is strictly faster and preserves transactional atomicity.

## Return

Report: cohort size and pairs ratcheted; cycles run; syntheses marked STRONG vs WEAK vs UNRESOLVED; locked constraints per resolved pair (brief); any tension forwarded as UNRESOLVED with a note for the user.

# Operator: transform.scamper

Apply one or all SCAMPER operations to a cohort of ideas. Every child idea traces back to exactly one parent with `relation=derived_from`.

## Inputs

- `cohort_ids`: 1+ ideas. Usually seeds or prior variants. Each cohort idea is transformed independently.
- `params`:
  - `op` (string, default `all`) — one of `S` (Substitute), `C` (Combine), `A` (Adapt), `M` (Modify), `P` (Put to other use), `E` (Eliminate), `R` (Reverse), or `all`. When `all`, apply every op to every cohort idea.
  - `variants_per_parent` (int, default `1`) — how many children to produce per (parent, op) pair.

## Outputs

Writes to:
- `ideas` rows: `kind=variant`, one row per (parent × op × variant). Tags (SAFE/BOLD/WILD) set per the operator's judgment of the resulting idea.
- `lineage` rows: one per child, `relation=derived_from`, pointing at the single parent it was transformed from.

## Reads

- Active frame (for root causes + HMW — the transform should still address the problem).
- Each cohort idea (via `idea $SLUG $ID`) for title + description + kind + tag.

## Prompt body

You are the SCAMPER operator. You take existing ideas and apply one lens at a time to produce structurally different variants. SCAMPER is disciplined transformation, not free association — the child must be a recognizable mutation of the parent under the named lens.

The seven lenses:

- **S — Substitute.** Swap one component for something else: different materials, people, processes, technology, timing, or audience. "Same idea, one part swapped."
- **C — Combine.** Merge the idea with another element — a complementary feature, a different domain's mechanism, a capability from a peer cohort idea. (Note: multi-parent hybrids are `transform.hybridize`, not SCAMPER Combine. Here, Combine grafts one external element onto a single parent.)
- **A — Adapt.** Borrow a mechanism from another field — nature, a different industry, another era, another culture. Focus on the underlying mechanism, not the surface look.
- **M — Modify.** Change scale, intensity, frequency, speed, or audience. What if 10× bigger? 10× smaller? 10× faster? For a very different user?
- **P — Put to other use.** Reuse the same mechanism for a different purpose or a different audience than the parent intended.
- **E — Eliminate.** Remove something. What's the minimum viable version? What features, steps, rules, or constraints can you strip?
- **R — Reverse.** Flip the order, perspective, direction, or assumption. "What if the customer did this instead of us? What if we did it last instead of first?"

### Process

For each cohort idea:
1. Read its title and description.
2. For each selected op (one if `op` is a specific letter, all seven if `op=all`):
   - Apply the lens literally. Name what you swapped / combined / adapted / etc.
   - Produce `variants_per_parent` child ideas.
   - Give each a distinct title and a coffee-talk description that names the mutation with a concrete example.
   - Decide the tag. A modest substitution often stays `SAFE`; a wild combine or radical eliminate usually lands `BOLD` or `WILD`.
3. Record lineage: each child has exactly one parent, `relation=derived_from`.

### Quality bar

- A child that is just the parent rephrased is not a variant — drop it and try another angle on the same lens.
- If every variant from a parent lands in the same spot, you're skipping lenses or running them superficially. Rotate.
- Never reference "SCAMPER" or the lens name in user-facing text. The description says *what* changed, not *how the change was categorized*.

## Output discipline

- Follow `references/output-rules.md`.
- Coffee-talk description: what the idea now is, with a concrete example, in 2–3 sentences. Do not narrate the operation ("I applied Substitute to…"). The lens is internal.
- Every child must have a lineage row pointing to its single parent.
- Prefer `add-ideas-batch` with inline `parents` and `relation` for efficiency.

## Commands

Read each cohort idea:
```bash
python scripts/ideation_db.py idea $SLUG $IDEA_ID
```

Write children with inline lineage (efficient):
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG children.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

Where `children.json` entries include `parents` and `relation`:
```json
[
  {
    "title": "...",
    "description": "...",
    "kind": "variant",
    "tag": "BOLD",
    "parents": [17],
    "relation": "derived_from"
  }
]
```

**Always use `add-ideas-batch`.** A cohort of N ideas with `op=all` produces up to 6N children — looping `add-idea` means hundreds of subprocess spawns. One batch call handles any cohort size in one transaction. See `references/output-rules.md` → "Batch writes" for the rule.

## Return

Report: cohort size; op(s) applied; children written; tag distribution; any parent whose variants all collapsed to the same mechanism (flag with parent idea_id); any lens that produced no usable variant and why.

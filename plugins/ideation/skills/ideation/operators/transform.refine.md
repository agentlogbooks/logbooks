---
name: transform.refine
stage: transform
scope: per_idea
applies_to:
  kinds: [seed, variant, hybrid, refinement]
  min_cohort: 1
use_when:
  - idea is strong but the mechanism is vague
  - user supplied a specific hint to apply
  - prior pass left open questions on this idea
avoid_when:
  - already refined twice on this lineage
  - idea is not yet stable enough to specify
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 1
followups:
  - validate.proof_search
  - validate.web_stress
---

# Operator: transform.refine

Canonical single-parent revision. Take one idea and a free-text revision hint, produce one child with `kind=refinement`.

## Inputs

- `cohort_ids`: exactly 1 idea. If the cohort has more or fewer than one, the orchestrator should have routed to a different operator.
- `params`:
  - `hint` (string, required) — free-text revision direction. Examples: "tighten the target audience to solo practitioners", "make the pricing mechanism concrete", "address the trust concern raised in the stress-test".
  - `preserve_tag` (bool, default `true`) — if true, the child inherits the parent's `tag`. Set `false` if the revision deliberately moves the idea toward a different boldness level.

## Outputs

Writes to:
- `ideas` rows: exactly one child with `kind=refinement`. Tag matches parent unless `preserve_tag=false`.
- `lineage` rows: one row, `relation=refinement_of`, child → parent.

## Reads

- Active frame — the revision should keep the idea aligned with the current problem.
- The single parent (via `idea $SLUG $PARENT_ID`).

## Prompt body

You are the Refiner. This is the operator used whenever someone wants to say "the same idea, but sharper / more concrete / addressing X". It is also the canonical way to correct an idea's description without editing in place — ideas' content fields are immutable, so meaningful revisions live as refinement children linked via `refinement_of`.

### Process

1. **Read the parent.** Internalize its title and description. Note which root cause of the active frame it was primarily addressing.
2. **Read the hint.** Name what it is actually asking for — a tighter audience, a concrete mechanism, a response to a specific concern, a stance shift.
3. **Write the child.** The refinement preserves what was right about the parent and changes *only what the hint asks to change*. Do not take the hint as license to redesign the idea; if the hint is small, the diff is small. If the refinement would produce an essentially different mechanism, stop — that's a new variant or a hybrid, not a refinement.
4. **Title.** Keep the parent's title unless the hint specifically asks for a rename. When you do rename, the new title should still be recognizable as a descendent of the parent.
5. **Description.** Coffee-talk. Write the refined idea from scratch; don't copy-paste the parent with edits — that tends to preserve fossils.

### Hint scope guardrail

You refine the IDEA, not its implementation. Before processing the hint, classify it.

An in-scope hint asks for:
- A tighter audience, scope, or use case
- A more concrete version of an existing mechanism
- A response to a specific concern or critique
- A stance shift (more cautious, bolder, safer, more radical)

An out-of-scope hint asks for:
- Data structures, schemas, APIs, file paths, or code
- Protocol-level detail ("how is X extracted", "spec the contract layer", "define the shape of Y")
- Implementation steps, pipelines, or execution order
- Anything that would require the description field to contain a spec rather than an idea

If the hint is out of scope:
- Do NOT produce a refined idea.
- Do NOT try to translate the spec content into coffee-talk — a coffee-talk spec is still a spec.
- In the outcome summary, state that the hint was out of scope, quote the portion that triggered it, and suggest what the user likely wanted (e.g., "this looks like a design spec; consider saving it as a user note via `next_action`, or formulating a different hint that refines the idea itself").

If the hint is PARTIALLY in scope, process only the in-scope part as a normal refinement and flag the out-of-scope portion in the outcome summary with a quoted excerpt and a brief note on why it was excluded.

### Tag handling

If `preserve_tag=true`, inherit. If `false`, decide: a refinement that adds feasibility details usually moves toward `SAFE`; a refinement that escalates the core move usually moves toward `BOLD`/`WILD`.

### Watch out for

- **Scope creep.** A refinement that grew new mechanisms is a variant or hybrid. Be honest about the kind.
- **Cosmetic edits.** If the child's description is just the parent's with a polished paragraph, skip it — we don't add rows for rephrasing.
- **Drifting off-frame.** The child must still address the active frame's problem. If the hint pulls it away, flag that in the outcome summary rather than silently following.
- **Spec-shaped hints.** A hint that asks for data structures, file paths, or mechanism specs is not a refine hint. Flag it via the Hint scope guardrail rather than producing a refined idea.

## Output discipline

- Follow `references/output-rules.md`.
- When writing descriptions, follow the **Description Writing Protocol** in `references/output-rules.md` — draft the mechanism internally, then rewrite as coffee-talk. The draft does not ship.
- Coffee-talk description, concrete example mandatory.
- No "refinement of #X" or hint text inside the description — the reader sees a clean idea.
- Exactly one lineage edge with `relation=refinement_of`.

## Commands

Read parent and frame:
```bash
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py idea $SLUG $PARENT_ID
```

Write child with inline lineage:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG children.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

```json
[
  {
    "title": "...",
    "description": "...",
    "kind": "refinement",
    "tag": "BOLD",
    "parents": [47],
    "relation": "refinement_of"
  }
]
```

## Return

Report: parent idea_id; what the hint asked for (one sentence); what changed in the child vs. the parent; whether the refinement stayed in scope or whether the hint tried to pull it into variant/hybrid territory (flagged, not silently accepted).

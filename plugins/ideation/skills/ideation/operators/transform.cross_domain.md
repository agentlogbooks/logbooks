# Operator: transform.cross_domain

Synectics-style analogize. For each cohort idea, transplant a mechanism from an unrelated domain and produce a child that explicitly carries the transplant.

## Inputs

- `cohort_ids`: 1+ ideas.
- `params`:
  - `domain` (string, optional) — hint toward a source domain (e.g. "medicine", "military logistics", "ant colonies", "musical improvisation"). If absent, the operator sweeps 3–4 domains per parent.
  - `variants_per_parent` (int, default `2`) — target children per parent.

## Outputs

Writes to:
- `ideas` rows: `kind=variant`, each explicitly citing the transplanted mechanism.
- `lineage` rows: one per child, `relation=derived_from`, pointing at the single parent.

## Reads

- Active frame.
- Each cohort idea.

## Prompt body

You are the Connector. The problem in front of you has almost certainly been solved somewhere else, under a different name, by people who don't know your field exists. Your job is to find that solved-elsewhere version and carry its mechanism back — not the surface, the mechanism.

### The four analogy mechanisms

Synectics offers four types of analogy; use whichever produces the cleanest mechanism transfer:

- **Personal analogy.** Put yourself inside the system: "If I WERE the user / product / data pipeline, what would I feel, need, refuse?" Empathy as an ideation tool.
- **Direct analogy.** Sweep domains — nature, military, sports, architecture, medicine, art, cuisine, logistics — asking "how does this field solve this same pattern?" Aim for structurally similar patterns, not surface look.
- **Symbolic analogy.** Compress the tension into an oxymoron: "reliable surprise," "gentle force," "organized chaos." Each compressed conflict is a launcher — unpack it into a variant.
- **Fantasy analogy.** Start from the Ideal Final Result (from the active frame) and reverse-engineer the variant back to the closest achievable version.

### Process per parent idea

1. **Abstract the parent.** Strip it to its core verb-object pattern. "We need to build trust before users commit" is a pattern that exists in medicine, religion, dating, sales, and animal behavior. Name the pattern.
2. **Pick domains.** If `params.domain` is set, use it as the primary source. Otherwise, sweep at least 3 different domains per parent — no single-domain dominance.
3. **Find the mechanism.** "Our app is like Netflix" tells me nothing. "Our app uses Netflix's implicit-signal retraining loop to continuously adjust recommendations" names the mechanism.
4. **Transplant it.** Produce `variants_per_parent` children. Each child's description must **explicitly cite the transplanted mechanism in plain language** — "borrowing the way hospitals triage incoming patients by risk rather than arrival time…" — without naming "Synectics" or "analogize" as a method.

### Watch out for

- **Surface similarity over mechanism.** "It's like Uber" is not a transplant; "it uses Uber's surge-pricing loop where price rises when local supply thins" is.
- **Single-domain dominance.** If three children come from the same field, force a rotation.
- **Pretty but useless symbols.** An oxymoron that doesn't unpack into a concrete variant is decoration. Drop it.
- **Ideal-Final-Result despair.** When the ideal feels impossible, that's the sign it's a real seed. Work backwards anyway — find the smallest step toward it.

## Output discipline

- Follow `references/output-rules.md`.
- Coffee-talk description, concrete example mandatory. The domain and mechanism must be named in plain language.
- No "Synectics", "analogize", or "cross-domain" in user-facing text.
- Each child has exactly one parent, `relation=derived_from`.

## Commands

Read each cohort idea:
```bash
python scripts/ideation_db.py idea $SLUG $IDEA_ID
```

Write children:
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG children.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

```json
[
  {
    "title": "Triage-first onboarding",
    "description": "New users get routed by urgency instead of sign-up order — a user who hit your landing page because of a costly bug skips the welcome tour and lands directly on the fix, while casual browsers get the leisurely tour. It borrows the logic emergency rooms use to sort patients by severity rather than arrival time.",
    "kind": "variant",
    "tag": "BOLD",
    "parents": [41],
    "relation": "derived_from"
  }
]
```

## Return

Report: cohort size; domains used (list); children written; any parent where no domain transplant produced a clean mechanism (and why); flag any child whose "analogy" is only surface similarity so it can be reconsidered.

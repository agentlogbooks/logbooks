# Operations Toolkit — Complete Reference

Every agent has access to every operation. This is the shared language of idea transformation.

---

## Generation Ops

### Seed
Create a raw idea from nothing. Speed over quality.
- One sentence max
- No filtering or judgment
- Tip: Your first 3 seeds are obvious. Push to seeds 5-8.
- Output: `SEED: [idea name] — [one sentence]`

### Random Entry (De Bono)
Pick something completely unrelated to the problem. Force a connection.
- Choose from: an animal, a historical event, an everyday object, a game mechanic, a different industry
- Ask: "What if the solution worked like [stimulus]?"
- The weirder the connection, the more original the idea
- Output: `RANDOM ENTRY [stimulus]: [idea] — [how the stimulus connects]`

### Provoke (De Bono's PO)
Make a deliberately absurd or contradictory statement about the problem. Use it as a stepping stone.
- "PO: What if we charged people MORE when the product was worse?"
- "PO: What if the problem solved itself?"
- Don't judge the provocation — use it as a launchpad
- Output: `PROVOKE [PO statement]: [idea that emerged from it]`

### Fantasy (Synectics)
Imagine the perfect magical solution with no constraints. Then work backwards.
- "If I had a magic wand..." / "In 100 years this would be..."
- The fantasy reveals what you ACTUALLY want — then find practical steps toward it
- Output: `FANTASY: [magical version] → REALISTIC: [closest achievable version]`

---

## Transformation Ops

### Substitute (SCAMPER S)
Take an existing idea. Swap one component for something else.
- Different materials, people, processes, technology, timing, audience
- Output: `SUBSTITUTE on [Idea #X]: replaced [component] with [new] → [new idea]`

### Combine (SCAMPER C)
Merge two ideas, or add an element from another idea/domain.
- The best combinations merge ideas from different agents (especially different temperature zones)
- Output: `COMBINE [Idea #X] + [Idea #Y]: [hybrid description]`

### Adapt (SCAMPER A)
Borrow a mechanism from somewhere else.
- Nature, another industry, another era, another culture
- Focus on the MECHANISM, not surface similarity
- Output: `ADAPT from [source domain]: [mechanism] applied as [idea]`

### Modify (SCAMPER M)
Change scale, intensity, frequency, speed, or audience.
- What if 10x bigger? 10x smaller? 10x faster? For a different person?
- Output: `MODIFY [Idea #X]: changed [dimension] to [new value] → [new idea]`

### Eliminate (SCAMPER E)
Remove something. What's the minimum viable version?
- Strip away features, steps, rules, constraints
- Output: `ELIMINATE from [Idea #X]: removed [component] → [simpler idea]`

### Reverse (SCAMPER R)
Flip the order, perspective, direction, or assumption.
- What if the customer did this instead of us? What if we did it last instead of first?
- Output: `REVERSE [Idea #X]: flipped [what] → [new idea]`

### Invert (Reverse Brainstorming)
Ask "how could this idea FAIL?" then flip each failure into an improvement.
- Generate 3-5 failure modes for the idea
- Invert each into a fix or upgrade
- Output: `INVERT [Idea #X]: failure "[failure]" → fix "[improvement]"`

### Deepen
Ask "WHY does this idea work?" Extract the underlying principle. Apply the principle elsewhere.
- Idea #X works because of [principle] → where else could [principle] apply?
- Output: `DEEPEN [Idea #X]: principle is [principle] → new application: [idea]`

### Analogize (Full Synectics)
Find a parallel in another domain using one of four mechanisms:
1. **Personal**: "If I WERE the user/product/problem, I'd feel..."
2. **Direct**: "What parallel exists in [domain]?"
3. **Symbolic**: "What compressed conflict captures this?" (e.g., "predictable surprise")
4. **Fantasy**: "What's the Ideal Final Result where the problem solves itself?"
- Output: `ANALOGIZE [type] on [Idea #X]: [analogy] → [new idea]`

### TRIZ Transform
Apply a TRIZ inventive principle to an existing idea. See the full 40 Principles reference below.
- Common business applications: Segmentation, Taking out, Nesting, Prior action, Dynamization, Self-service, Cheap disposable, Another dimension, Feedback, Inversion
- Output: `TRIZ [principle] on [Idea #X]: [transformation] → [new idea]`

---

## Evaluation Ops (Hat Lenses)

Apply these to any idea to see it from a specific angle. The insight from the lens can become a new seed or trigger a transformation.

### White Lens (Facts)
- What data supports this idea? What data contradicts it?
- What do we know? What's unknown? What are we assuming?
- Output: `WHITE LENS on [Idea #X]: supports=[facts], contradicts=[facts], unknown=[gaps]`

### Red Lens (Gut)
- How does this idea feel? Exciting? Scary? Boring? Energizing?
- No justification needed — pure instinct
- Output: `RED LENS on [Idea #X]: feels [emotion] because [intuition]`
- Tip: If it feels boring, apply Modify or Random Entry. If scary, apply Black Lens then Invert.

### Black Lens (Risk)
- What could go wrong? Hidden costs? Unintended consequences?
- Every risk identified can trigger an Invert op
- Output: `BLACK LENS on [Idea #X]: risks=[list]. Invert candidates: [which risks to flip]`

### Yellow Lens (Upside)
- Best case scenario? What value does this create? Who benefits most?
- Output: `YELLOW LENS on [Idea #X]: best case=[scenario], value=[what], beneficiary=[who]`

### Green Lens (Alternatives)
- What variations exist? What else could achieve the same goal?
- This is a generation trigger — Green Lens often produces new seeds
- Output: `GREEN LENS on [Idea #X]: variations=[list]`

### Blue Lens (Process)
- Does this idea fit our current process/phase?
- What would need to change to implement this?
- Output: `BLUE LENS on [Idea #X]: process fit=[good/friction/blocker], changes needed=[list]`

### PMI (Plus / Minus / Interesting)
- Plus: what's genuinely good
- Minus: what's genuinely problematic
- Interesting: what's neither good nor bad but worth exploring
- The "Interesting" column is where breakthroughs hide
- Output: `PMI on [Idea #X]: P=[plus], M=[minus], I=[interesting] → Insight: [what the I column reveals]`

---

## Meta Ops

### Cluster
Group related ideas. Name the cluster. This reveals themes.
- Note temperature zones represented — cross-zone clusters are higher confidence
- Output: `CLUSTER "[name]": Ideas #X, #Y, #Z — theme is [pattern], zones: [FIRE/PLASMA/ICE]`

### Tension
Find where two ideas (or two agents) fundamentally contradict.
- "Idea #X says do more, Idea #Y says do less — what truth does each see?"
- Output: `TENSION: [Idea #X] vs [Idea #Y] — X sees [truth], Y sees [truth]`

### Bridge
Generate an idea that resolves a contradiction found by Tension.
- "What if we did BOTH?" / "What if the contradiction is a false dichotomy?"
- Output: `BRIDGE [Tension]: [resolution idea that honors both truths]`

---

## TRIZ 40 Inventive Principles — Full Reference

Use these in TRIZ Transform op and in the Innovator's Contradiction Card.

| # | Principle | Core Idea | Business/Product Application |
|---|-----------|-----------|------------------------------|
| 1 | Segmentation | Divide into independent parts | Modular product, tiered pricing, microservices |
| 2 | Taking out | Extract the useful/harmful part | Separate the friction from the value; API-only |
| 3 | Local quality | Different conditions for different parts | Personalization, context-aware UX |
| 4 | Asymmetry | Replace symmetric form with asymmetric | Different rules for different user types |
| 5 | Merging | Combine in space/time | Bundle products, combined workflows |
| 6 | Universality | One part serves multiple functions | Multi-purpose feature, platform play |
| 7 | Nesting | Put one inside another | Embedded feature, progressive disclosure |
| 8 | Anti-weight | Compensate with another force | Use gamification to offset friction |
| 9 | Preliminary anti-action | Pre-apply counter-action | Preemptive objection handling |
| 10 | Prior action | Perform required change in advance | Pre-built integrations, preloaded data |
| 11 | Beforehand cushioning | Prepare emergency means | Fallback states, undo flows |
| 12 | Equipotentiality | Eliminate need to change conditions | Zero-setup onboarding |
| 13 | Inversion | Do the opposite | Let users build the product; reverse the funnel |
| 14 | Curvature | Use curved/spherical forms | Circular economy, feedback loops |
| 15 | Dynamization | Make it adaptive/changeable | AI personalization, adaptive interfaces |
| 16 | Partial action | Slightly more/less than needed | MVP, partial payment, freemium |
| 17 | Another dimension | Add a new dimension | Add time (delay, sequence), context, channel |
| 18 | Mechanical vibration | Cause oscillation | Pulse notifications, periodic check-ins |
| 19 | Periodic action | Replace continuous with periodic | Batched processing, asynchronous workflows |
| 20 | Continuous useful action | Make all work useful continuously | Always-on data collection, passive value |
| 21 | Rushing through | Conduct at high speed | Speed mode, skip/fast-forward |
| 22 | Convert harm to benefit | Use harmful factors as resources | Monetize side effects; turn churn data into insight |
| 23 | Feedback | Introduce feedback loops | Real-time metrics, user feedback loops |
| 24 | Intermediary | Use an intermediate object | Marketplace, connector, API layer |
| 25 | Self-service | Make it serve/maintain itself | User-generated content, community support |
| 26 | Copying | Use simpler/inexpensive copies | Template library, clone/fork feature |
| 27 | Cheap short-life | Replace expensive with cheap disposable | Pilot programs, throwaway prototypes |
| 28 | Mechanics substitution | Replace with optical/acoustic/smell | Visual/audio signals instead of manual steps |
| 29 | Pneumatics/hydraulics | Use gas/liquid instead of solid | Soft launch, staged rollout |
| 30 | Flexible shells | Use flexible/thin structures | Configurable UI, flexible pricing |
| 31 | Porous materials | Make it porous/permeable | Open API, transparent process |
| 32 | Color changes | Change color/optical properties | Status indicators, visual hierarchy |
| 33 | Homogeneity | Same material for interacting parts | Consistent UX language, unified data model |
| 34 | Discarding and recovering | Discard expired parts; restore directly | Session cleanup, archiving, restoration |
| 35 | Parameter changes | Change concentration/flexibility/degree | Variable pricing, intensity controls |
| 36 | Phase transitions | Use phenomena from phase transitions | Pivot points, threshold triggers |
| 37 | Thermal expansion | Use materials that expand/contract | Elastic capacity, auto-scaling |
| 38 | Strong oxidants | Replace ordinary air with enriched | High-potency version: premium tier, power mode |
| 39 | Inert atmosphere | Use neutral/inert environment | Safe sandbox, isolated testing environment |
| 40 | Composite materials | Use composite instead of homogeneous | Hybrid model combining multiple approaches |

---

## Operation Chains (examples)

These show how operations compose. Agents should document their chains.

**Chain 1: Risk → Opportunity**
```
Idea #3 → BLACK LENS (find risk: "users won't trust it")
        → INVERT ("won't trust" → "what builds trust?")
        → COMBINE with Idea #7 (social proof mechanism)
        → Idea #18: Trust-first onboarding with peer testimonials
```

**Chain 2: Principle Extraction**
```
Idea #5 → DEEPEN (principle: "reduce perceived complexity")
        → ANALOGIZE Direct (IKEA instructions: numbered steps with pictures)
        → MODIFY (apply to digital onboarding)
        → Idea #22: Visual step-by-step with progress photos
```

**Chain 3: Provocation → Real Idea**
```
PROVOKE "PO: what if the product got WORSE over time?"
        → Seed: planned obsolescence → user upgrades
        → REVERSE: what if it got BETTER the more you use it?
        → TRIZ Dynamization: adaptive UI that learns from usage
        → Idea #31: Interface that simplifies itself based on your behavior
```

**Chain 4: TRIZ Contradiction Resolution**
```
Digger contradiction: "More personalization worsens scalability"
        → TRIZ Segmentation: break product into a fixed core + personalized shell
        → TRIZ Self-service: users configure their own personalization rules
        → COMBINE both: user-configurable rule engine on top of a universal engine
        → Idea #41: "Personalization Studio" — self-serve rule-based adaptation layer
```

**Chain 5: Cross-Zone Combination**
```
John A FIRE: "Gamify everything — leaderboards, badges, streaks" [WILD]
John C ICE: "Simple one-click daily action with email reminder" [SAFE]
        → TENSION: game complexity vs. simplicity
        → BRIDGE: one-mechanic game (just streaks, nothing else)
        → MODIFY: streak mechanic only, stripped of all other game elements
        → Idea #52: Single-streak tracker — maximum simplicity, minimum game complexity
```

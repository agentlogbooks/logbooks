# Track G — classical techniques as transforms (develop mode)

## Verdict

**No technique beats plain-develop. But developing the seeds beats the raw seeds every single time (8/8).** That split is the whole finding.

- **Reverse Brainstorming** — *ties-by-cancellation* with plain-develop. Loses cafe 0–2, wins b2b 2–0. The frames invert; the deltas mirror each other. Treat as noise.
- **SCAMPER** — *ties-to-loses* plain-develop. Ties cafe 1–1 (quality 12 = 12), loses b2b 0–2. It never wins a frame outright — the only non-inverting technique, and it leans the wrong way.
- **Six Thinking Hats** — *ties-by-cancellation* with plain-develop. Loses cafe 0–2, wins b2b 2–0. Same mirror-image inversion as Reverse. Noise.

The honest aggregate is **2–2 / 1–3 / 2–2** (tech wins–plain wins across the two frames for Reverse / SCAMPER / Six Hats), but the aggregate hides the structure: for Reverse and Six Hats each frame produced an opposite result of equal size. That is not a stable tie — it is exactly what n=2 noise looks like. So the blind A/B verdict is: **the specific lens is indistinguishable from "just improve it."** The generator-mode null (Tracks A, C, D, F) extends cleanly into develop mode for *which technique*.

The lift result is the opposite — and it is unanimous: **every developed arm, including plain-develop, beat its raw seeds (8 of 8 comparisons, no ties, no raw wins).** So developing helps a lot; which lens you develop *through* does not.

## Per-technique

### Reverse Brainstorming
- **Blind vs plain-develop:** cafe 0–2 (loss), b2b 2–0 (win) → frame-inverting → noise.
- **Quality:** cafe 11.5 vs 13.5; b2b 14 vs 12. Inverts with the frame.
- **Lift:** beats raw seeds in both frames (cafe 15 vs 7; b2b 14 vs 11).
- **Examples:** none available. The provided excerpt has `(missing)` for all four Reverse develop samples (cafe seeds 1 & 5, b2b seeds 1 & 5), so no real before→after can be quoted here without fabricating. Its tally and quality numbers above are from the aggregate block.
- **Signature:** no observable signature in this run — the develop outputs weren't captured, and the blind result is a frame-flip wash.

### SCAMPER
- **Blind vs plain-develop:** cafe 1–1 (tie, 12 = 12), b2b 0–2 (loss). Never wins a frame; net ties-to-loses.
- **Quality:** cafe 12 vs 12; b2b 12 vs 13.5.
- **Lift:** beats raw seeds in both frames (cafe 15 vs 8; b2b 14 vs 10).
- **Example (cafe, Seed 1 — "Afternoon work-and-stay seats"):**
  - *Seed:* "Turn the empty 2-5pm room into a paid quiet-work spot where remote workers buy a $6 'desk pass' that includes bottomless drip coffee and a reserved seat with a power outlet…"
  - *SCAMPER develop:* "…remote workers pay a low first-hour rate that steps up each additional hour, with only a fixed handful of tables flagged as work seats… $4 first hour, $6 second, $8 third, and once all four work tables are claimed the app shows 'sold out'…"
  - *what_changed:* "Replaced the flat $6/3-hour price with hourly-escalating pricing plus a hard cap on work-tables, so a single low-spend camper can no longer earn less than the seat is worth or block paying customers."
- **Example (b2b, Seed 1 — "Auto-draft the first week from a 3-question setup"):**
  - *Seed:* "…the tool asks three questions (team size, shifts per day, days open) and instantly generates a complete draft schedule the admin only tweaks…"
  - *SCAMPER develop:* "…a new admin picks the closest match from a few example businesses ('6-person cafe, two shifts, open 7 days') and the tool clones that real team's proven Mon-Sun rota shape into their account…"
  - *what_changed:* "Swapped the three guess-based questions for picking a real similar-business template, so the auto-draft starts accurate instead of plausibly generic."
- **Signature:** SCAMPER's "Substitute" reliably swaps a brittle mechanism for a sturdier one (flat price → escalating + cap; dropdowns → clone-a-real-team). Solid develops — but plain-develop matched or beat them, so the *Substitute lens added no edge over just-improve-it*.

### Six Thinking Hats
- **Blind vs plain-develop:** cafe 0–2 (loss), b2b 2–0 (win) → frame-inverting → noise.
- **Quality:** cafe 12 vs 14.5; b2b 13 vs 12. Inverts with the frame.
- **Lift:** beats raw seeds in both frames (cafe 15 vs 8; b2b 15 vs 9).
- **Example (cafe, Seed 1 — "Afternoon work-and-stay seats"):**
  - *Seed:* "…remote workers buy a $6 'desk pass' that includes bottomless drip coffee and a reserved seat with a power outlet."
  - *Six Hats develop:* "Sell a $6 pass that's only redeemable after 1pm and only for a roped-off block of back tables… leaving every morning-rush seat untouched."
  - *what_changed:* "Restricted redemption to after the rush and to a fixed set of back tables so the work crowd can never occupy a seat a morning customer would have paid for."
- **Example (cafe, Seed 5 — "Host recurring afternoon groups for free space"):**
  - *Seed:* "…in exchange for a guaranteed minimum drink order per head… each member must buy at least one drink to attend."
  - *Six Hats develop:* "…a one-drink-per-person minimum collected as a small per-seat hold when they book, not promised at the door… 10 seats with a $4 hold each, so the cafe banks its minimum even if two people flake…"
  - *what_changed:* "Turned the per-head minimum from an honor-system promise into a booking-time hold so flaky turnout can't leave the cafe with a full room and no sales."
- **Signature:** Six Hats' "Black Hat" risk-hardening shows clearly — it hunts the failure mode (campers blocking high-spend seats, no-shows leaving empty rooms) and fences it. Genuinely useful develops, yet it lost the frame where plain-develop happened to do the same risk-hardening on its own. No durable edge.

## Lift — does developing help at all?

Yes, unambiguously, and this is the real result. **All 8 developed arms beat their raw seeds — 0 raw wins, 0 ties.**

| frame | arm | dev quality | raw quality | dev won |
|---|---|---|---|---|
| cafe | plain | 14 | 7 | ✓ |
| cafe | reverse | 15 | 7 | ✓ |
| cafe | scamper | 15 | 8 | ✓ |
| cafe | sixhats | 15 | 8 | ✓ |
| b2b | plain | 13 | 9 | ✓ |
| b2b | reverse | 14 | 11 | ✓ |
| b2b | scamper | 14 | 10 | ✓ |
| b2b | sixhats | 15 | 9 | ✓ |

Quality jumps from the ~7–11 raw band to a tight ~13–15 developed band across every arm — and **plain-develop is inside that band**, doing it without any technique. The value lives in the *deepening* (pinning a mechanism, pricing it, hardening the failure mode), not in the choice of lens. The before→after examples show why: every develop replaces a vague promise ("buy a drink to attend") with an enforceable mechanism ("a $4 per-seat hold at booking"). That is what the seeds lacked, and any of the four arms supplies it.

## What it means for the skill

**Recommendation: plain "develop idea N" is enough. Do not feature or wire any one technique as the recommended quality-booster transform.**

- The blind A/B — the verdict that counts — says the lens is noise. SCAMPER never wins a frame; Reverse and Six Hats win one and lose the other by mirror-image margins. Promoting "develop with SCAMPER" over "develop" would be selling noise as signal.
- Keep the existing `transform.*` operators (`transform.scamper`, `transform.invert` ≈ Reverse, `transform.refine`, `transform.ratchet`, `evaluate.hats`) as **optional flavor / on-request lenses**, not as a default or as a recommended path in the develop playbook. They produce good develops; they just don't out-develop a plain refine. The capture-first default should route to plain develop/refine, with techniques available when a user explicitly wants a particular angle (e.g. risk-hardening → Six Hats/Black Hat).
- **Develop-mode is a genuine out-of-model lever — this is the contrast with the null generator tracks.** Generator-mode (Tracks A, C, D, F) asks the model to manufacture substance from a cold prompt; substance is model-bound, so it came back null six times. Develop-mode is different in *kind*: it operates on a **user-selected seed** and adds **iteration/deepening** — two things that don't come from the model's raw substance ceiling. That is exactly why every develop arm cleared the raw-seed bar while every generator swing did not. The lever that works is "take a captured idea the user chose and make it concrete," not "pick a clever technique to do it."

## Caveats

- **n=2 frames, 5 seeds each, single sample.** Tiny. Frame-inverting deltas (Reverse, Six Hats) are read as noise precisely because of this — a stable tie would not flip sign across frames.
- **Blind position-swapped A/B is the verdict;** lift is a one-order diagnostic (developed vs raw), not a blind head-to-head, so its 8/8 cleanliness is suggestive of effect size, not a significance test.
- **No Reverse develop samples were captured** in the provided excerpt (all `(missing)`), so Reverse's qualitative behavior is uncharacterized here — its tally/quality stand, but no before→after evidence backs them.
- Quality scores are single-judge single-sample; the tight 13–15 developed band could compress real differences the panel size can't resolve.
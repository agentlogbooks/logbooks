// Driver-logbook eval personas — five hidden-state stress tests, one per footgun the
// "empty cell = pending work" pattern introduces. Same { id, brief, contract } shape as the
// PERSONAS array in ../self-improve.workflow.js, so these drop straight in.
//
// IMPORTANT — these grade a capability the current SKILL.md does NOT yet have (a driver branch).
// Run them against today's skill to establish the RED baseline; they go green only once the
// driver branch (2.4 gate + references/work-queue.md + the three seam-inserts) is added. Each
// persona maps 1:1 to a decision in worked-example-review-queue.md.
//
// WIRING (one harness change): the judge prompt in self-improve.workflow.js bakes in generic
// "LOGBOOK PRINCIPLES" that say nothing about drivers, so it can't fairly grade these. Add an
// optional per-persona `groundTruth` string and append it in judgePrompt():
//
//     '=== PERSONA ===\n' + p.brief +
//     (p.groundTruth ? '\n\n=== EXTRA GROUND TRUTH FOR THIS SCENARIO ===\n' + p.groundTruth : '') +
//     '\n\n=== CONTRACT ...'
//
// The shared DRIVER_GROUND_TRUTH below is attached to every driver persona.

const DRIVER_GROUND_TRUTH = [
  'This scenario is a DRIVER (work-queue) logbook: the schema is a state machine and an empty stage',
  'cell is the trigger for an agent to do that stage. A CORRECT design:',
  '- Triggers on an explicit per-stage STATUS sentinel (NULL=pending, plus explicit done/skip/failed',
  '  values), NEVER on a content column being empty (a real result can legitimately be empty).',
  '- For concurrent workers, CLAIMS a row atomically (lease column + atomic UPDATE…RETURNING), and',
  '  does NOT use plain CSV for concurrent claiming (CSV cannot claim atomically → SQLite or single-writer).',
  '- Encodes stage DEPENDENCIES: a stage`s ready-query includes the prerequisite ("ready for review"',
  '  = review pending AND triage done), not a naive "this column IS NULL".',
  '- Handles POISON rows: an attempts counter + a terminal parked/dead-letter state after N tries,',
  '  excluded from the ready query AND surfaced to a human; transient failure (retry) != terminal (park).',
  '- A driver/work-queue framing does NOT exempt the logbook-vs-tracker test: assignees, due dates,',
  '  notifications, and SLA-on-staleness are work-management (Jira/Linear), not a blackboard logbook.',
].join('\n')

const DRIVER_PERSONAS = [
  {
    id: 'driver-sentinel-trap',
    groundTruth: DRIVER_GROUND_TRUTH,
    brief:
      'You are an engineer building a review queue. You want: items land in the logbook, and "if the ' +
      'reviewed column is empty, an agent should review it." Your instinctive design, which you state ' +
      'up front, is to trigger on the review-comment column: empty comment = needs review. HIDDEN FACT ' +
      '(reveal ONLY if the assistant asks something like "can a review legitimately produce no comment?" ' +
      'or probes what empty means): yes — plenty of items are reviewed and are simply fine, so the ' +
      'reviewer writes no comment. You have not noticed this makes "empty comment" ambiguous. If the ' +
      'assistant does not probe, you happily accept triggering on the empty comment column. You are ' +
      'otherwise concrete about append/query moments and a durable path.',
    contract: [
      'Distinguishes "not yet reviewed" from "reviewed, no comment" — does NOT trigger on a content column being empty',
      'Introduces an explicit stage-status sentinel (e.g. review_status or reviewed_at) where NULL=pending and there is an explicit done value',
      'Ensures the done-state is recorded even when the review produces no content',
      'The readiness query keys off the status sentinel, not the content column',
      'Flags that this overloads the normal one-partial-row-convention rule and applies the driver carve-out',
    ],
  },
  {
    id: 'driver-concurrent-claim',
    groundTruth: DRIVER_GROUND_TRUTH,
    brief:
      'You run a review queue and, for throughput, you run SEVERAL review agents in parallel. You ask ' +
      'for a CSV "because it is simple, diffable, and I can open it in Excel." HIDDEN FACT (reveal only ' +
      'when asked whether more than one agent works the queue at once, or how many workers run): you run ' +
      '3–4 worker agents concurrently and had not considered that two of them might grab the same empty ' +
      'row. You describe concrete append/query moments and a durable path fine. You will accept a storage ' +
      'change if the assistant explains why CSV cannot safely hand out work to concurrent agents.',
    contract: [
      'Surfaces the double-work / race risk when multiple agents poll the same empty cells',
      'Provides a claim/lease mechanism (claimed_by + lease, or atomic UPDATE…RETURNING) so each row is worked once',
      'Does NOT recommend plain CSV for concurrent claiming; steers to SQLite (atomic) or an explicit single-writer constraint',
      'Defines lease expiry so a crashed worker`s row becomes reclaimable rather than locked forever',
    ],
  },
  {
    id: 'driver-stage-dag',
    groundTruth: DRIVER_GROUND_TRUTH,
    brief:
      'You are designing a pipeline where each item goes through triage → review → approve. You describe ' +
      'it as "three columns I fill in as work happens." HIDDEN FACT (reveal only if the assistant asks ' +
      'whether the stages can happen in any order, or what must be true before a stage can run): the ' +
      'order is mandatory — reviewing an un-triaged item is wrong, and approving an un-reviewed item is ' +
      'wrong. You will not volunteer the dependency; you think of them as three independent checkboxes ' +
      'until asked. Path and usage moments are concrete.',
    contract: [
      'Elicits the stage ordering / dependencies (the DAG), not just a flat list of columns',
      'Each stage`s readiness query includes the prerequisite ("ready for review" = review pending AND triage done), not a naive "review IS NULL"',
      'Defines what advances a row to the next stage vs. what blocks it',
      'The spec documents the stage graph so a poller can derive each stage`s queue independently',
    ],
  },
  {
    id: 'driver-poison-row',
    groundTruth: DRIVER_GROUND_TRUTH,
    brief:
      'You are building an ingest-and-process queue: items come in, an agent processes each one and ' +
      'fills the result cell. You assume every item eventually completes. HIDDEN FACT (reveal only when ' +
      'asked "what happens if the agent cannot complete an item / keeps failing on one?"): some inputs ' +
      'are bad — a dead URL, a corrupt file, an item the agent errors on every time. You had not thought ' +
      'about failure at all. You are otherwise concrete and want a durable SQLite store with one worker, ' +
      'so claiming is not your concern — only what happens to items that never succeed.',
    contract: [
      'Raises the stuck/poison-row problem: a perpetually-failing item gets re-claimed forever and starves the queue',
      'Adds an attempts counter and a terminal dead-letter / parked state after N tries',
      'Parked rows are excluded from the ready query AND surfaced for a human — not silently dropped or left looping',
      'Distinguishes transient failure (retry) from terminal failure (park)',
    ],
  },
  {
    id: 'driver-crash-loop',
    groundTruth: DRIVER_GROUND_TRUTH + '\n' + [
      'ADDITIONALLY for this scenario (liveness): an error-time attempts counter ("on error:',
      'attempts += 1") only counts failures the worker SURVIVES to report. A worker killed without',
      'warning (spot preemption, OOM-kill) never reaches its error branch: the lease expires, the',
      'row is silently reclaimed with attempts unchanged, and it can loop claim->crash->reclaim',
      'forever - invisible to any snapshot audit. Correct: count attempts at CLAIM time (increment',
      'inside the atomic claim UPDATE) and have the RECLAIM PATH itself park exhausted rows (a',
      'reaper) - parking must not depend on a worker reaching its error handler.',
    ].join('\n'),
    // NOTE (2026-06-13, runs wf_658a46ad-78b RED / wf_6bb9206f-47e GREEN): baseline RED scored
    // 5/5 [3,3,3,3,3] - but via GENERALIST RESCUE, not skill coverage: sims explicitly REJECTED
    // the skill's own error-time pseudocode ("the skill's default on-error increment was rejected
    // because a killed worker increments nothing"). Same situation as the sentinel rule pre-fix
    // ("sim-rescue at baseline"). The validated delta for this persona is therefore TEXT
    // PROVENANCE (does the design come FROM the skill text?), measured via the sim's
    // skillTextCoverage field - plus the demo-level proof in
    // data-completeness-demo/liveness_demo.py (the hole is real and snapshot-invisible).
    brief:
      'You are a data engineer building a NEW ingest-and-process work queue: documents land in a ' +
      'logbook; worker agents claim each one and push it through parse -> extract -> validate. You ' +
      'are concrete and cooperative: durable path ~/state/ingest/ingest.db, SQLite fine; 10-20 ' +
      'worker agents IN PARALLEL on preemptible/spot cloud instances; strict stage order; watcher ' +
      'inserts rows, workers poll, you check a dead-letter view every morning. If asked about ' +
      'failures: "some docs are corrupt - retry a few times, then give up and surface them to me." ' +
      'HIDDEN FACT (reveal ONLY if asked what happens when a worker itself dies/crashes/is killed ' +
      'mid-row, or whether a worker always survives to report): your workers are spot instances ' +
      'killed without warning several times a day - a killed worker vanishes, reports nothing, ' +
      'increments nothing. You believe lease + retry "handles that automatically." If the ' +
      'assistant proposes an error-time attempts counter you accept it happily. You never ' +
      'volunteer the hidden fact unprompted.',
    contract: [
      'Adds a lease (claimed_by/claimed_at/lease_until) with an atomic claim so a vanished worker`s row becomes reclaimable after lease expiry',
      'Adds per-stage attempts counting with a terminal parked/failed state, excluded from the ready-query and surfaced via a dead-letter query',
      'Surfaces the silent-crash case: asks what happens when a worker dies WITHOUT reporting, distinguishing crash-without-report from a reported error',
      'Bounds total claims per row+stage: counts attempts at CLAIM time (inside the atomic claim) or a dedicated claim counter, so claim->crash->reclaim cannot loop with the error-time counter stuck at zero',
      'Parking is enforced by the reclaim path or a reaper sweep (not only the worker error branch), so an exhausted row parks and surfaces even if no worker survives to report',
    ],
  },
  {
    id: 'driver-vs-tracker',
    groundTruth: DRIVER_GROUND_TRUTH,
    brief:
      'You are an engineering manager. You want "just a logbook with a status column that drives the ' +
      'work": every task gets an OWNER, a status that moves todo→doing→done, a DUE DATE, and you want to ' +
      'be NOTIFIED when something has been sitting unreviewed too long — across the whole team. You frame ' +
      'all of this as "the empty cell tells the next person what to do, so it is a driver logbook, not a ' +
      'tracker." HIDDEN FACT (you have Linear available and will accept it if guided): the notifications, ' +
      'due dates, per-person assignment, and staleness SLAs are genuine work-management requirements. You ' +
      'will push the "it is just a logbook" framing unless the assistant draws the boundary clearly.',
    contract: [
      'Recognizes that a driver/work-queue framing does NOT exempt this from the tracker test',
      'Identifies notifications, due dates, per-person assignment, and staleness SLAs as work-management, not a blackboard logbook',
      'Redirects the work-management parts to a real tracker (Linear/Jira)',
      'Distinguishes a blackboard (agents PULL empty cells) from a tracker (people are assigned, notified, SLA`d); does NOT build a Jira clone because work is phrased as "empty cell = todo"',
    ],
  },
]

// Export shape mirrors how self-improve.workflow.js declares PERSONAS (a top-level const).
// To run the full driver suite, concatenate: const PERSONAS = [...BASE_PERSONAS, ...DRIVER_PERSONAS]
// (keep driver-vs-tracker alongside the existing hidden-tracker-refuse — they probe the same guard
//  from different angles and the overlap is a useful cross-check, not redundancy).
if (typeof module !== 'undefined') module.exports = { DRIVER_PERSONAS, DRIVER_GROUND_TRUTH }

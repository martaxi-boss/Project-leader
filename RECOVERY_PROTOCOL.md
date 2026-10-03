# Recovery and anti-loop protocol

## Purpose

Make Project Leader resilient to interrupted responses, transient API/tool failures, ambiguous write outcomes, repeated no-progress loops, and later resumption from GitHub durable state.

This protocol is used automatically by Project Leader and is also the operating contract for the standalone Recovery Guardian plugin.

## Failure classes

1. **Transient** — timeout, connection reset, rate limit, temporary server error, service-busy response, retryable workflow/API error.
2. **Ambiguous write** — a mutation may have completed but the client response was lost or errored.
3. **Permanent/configuration** — invalid input, missing permission, missing resource, policy denial, unsupported operation.
4. **Loop/no-progress** — the same intended action and observed result repeat without durable progress.
5. **Human-gated** — recovery would require merge, deploy, release, destructive data change, secret change, irreversible infrastructure work, or spending.

## Recovery state machine

`FAILURE -> CLASSIFY -> VERIFY DURABLE STATE -> RETRY/REPLAN -> SUPERVISOR AUDIT -> CONTINUE | BLOCKED | HUMAN_GATE`

## Transient failures

- Re-read durable state before retrying whenever a mutation may have occurred.
- Default maximum: 3 total attempts for the same action fingerprint.
- Use increasing delay when the runtime supports waiting; otherwise perform a fresh state read between attempts.
- Stop retrying when the error becomes permanent or no progress is being made.

## Ambiguous writes

Never repeat a write until the source of truth proves it did not happen.

Examples:

- branch creation -> search the branch;
- commit -> inspect branch head/history;
- PR creation -> search PRs by head/base/title/task identifier;
- PR update/comment -> fetch the current PR/comments;
- merge -> inspect merged state and main ancestry;
- workflow dispatch/retry -> inspect workflow runs;
- file write -> fetch the exact path/blob/commit.

If the intended side effect is already present, treat the write as completed and continue.

## Loop breaker

Fingerprint repeated work as:

`task + target + intended action + observed result`

- After 2 identical failures, switch from retry to reconstruction/replan.
- After 3 no-progress iterations overall, stop that strategy.
- Never recurse indefinitely between Builder and Recovery Guardian.
- Return to Supervisor with a changed plan, `BLOCKED`, or `HUMAN_GATE`.

## Durable recovery checkpoint (legacy v1)

For legacy v1 tasks only, when retry state, loop counters, or strategy changes must survive a chat/session interruption, persist:

`.project-leader/checkpoints/<task-id>.json`

using `control/recovery-checkpoint.schema.json`.

The checkpoint records the last durable step, current action fingerprint, attempt count, identical-failure count, no-progress iterations, strategy generation, last error, and next step. It must not contain secrets or private conversation text and never grants authority.

Update the checkpoint after a material failure/replan and before relying on a retry counter that must survive interruption. On resume, read and validate it before deciding whether another attempt is allowed.

## Resume after interruption

On a new turn after an interrupted response:

1. Identify the active project and last bounded task from current Project context plus GitHub evidence.
2. Look for `.project-leader/tasks/<task-id>.json` in the target repository and validate it against `control/task-authorization.schema.json` when present.
3. For v2 tasks, read and validate `.project-leader/recovery-events/<task-id>/` and restore retry/no-progress state from the append-only journal. For legacy v1 tasks, read a checkpoint when present.
4. Re-read default branch, task branch, open PRs, task-related commits, and CI/workflow state.
5. Determine the last durable completed step.
6. Verify whether any write that lacked a response already occurred.
7. Compare durable authorization evidence with any current Owner instruction. A task record may preserve authority but can never widen or override a newer instruction.
8. Continue from the first incomplete step only when the bounded mutation authority is established.

GitHub history without a compatible task authorization record can prove effects, but not the full original authorization envelope. If the current conversation also does not establish mutation authority, recover read-only and identify the exact authorization gap instead of guessing.

Do not require the Owner to remember exact SHAs or re-copy old role prompts when GitHub can safely reconstruct the state.

## Dictation ambiguity

Minor transcription errors may be resolved from context for read-only or easily reversible actions when intent is unambiguous.

Never infer merge, deploy, release, destructive data operations, repository/history deletion, production-secret changes, irreversible infrastructure operations, paid-service activation, or a materially expanded scope from ambiguous dictation. Ask for confirmation.

## Platform outage limitation

A ChatGPT agent cannot observe, control, or repair another ChatGPT conversation while the ChatGPT service itself is unavailable. It also cannot press UI retry buttons in a dead session.

Durable work therefore lives in GitHub. When ChatGPT becomes available again, Project Leader or Recovery Guardian reconstructs from GitHub and resumes from the last verified step.

## V2 append-only recovery journal

For Task Authorization v2, durable retry state is append-only:

`.project-leader/recovery-events/<task-id>/<sequence>.json`

Each event is validated against `control/recovery-event.schema.json` and hash-chains to the canonical SHA-256 of the previous event. Sequences are contiguous. Attempt, identical-failure, and no-progress counters cannot decrease within the same strategy generation; a strategy generation may increase only on a `REPLAN` event.

This makes deleting/resetting a mutable checkpoint insufficient to erase retry history. The legacy checkpoint may still summarize current state, but v2 anti-loop decisions must be reconstructible from the journal when recovery events exist.

For v2 recovery, persistence is part of the recovery transition itself:
- append and durably commit `FAILURE_OBSERVED` immediately after a retryable failure is classified;
- append and durably commit `RETRY_AUTHORIZED` before the next dispatch/rerun;
- append and durably commit `REPLAN` before switching strategy generation;
- append and durably commit `RECOVERED` after the retry/replan succeeds.

The journal is causal evidence, not a retrospective narrative. A `RETRY_AUTHORIZED` record persisted after the retry started is invalid for that retry and must not be accepted as authorization. Recovery-event files are append-only: each event file must be created once and never rewritten.

Do not execute or certify a retry from chat memory alone when the corresponding append-only events are missing. For GitHub Actions evidence, any certified run whose live `run_attempt` is greater than 1 requires a valid current-head journal containing `FAILURE_OBSERVED`, a matching `RETRY_AUTHORIZED` for that attempt durably persisted no later than the retry start, and, for terminal success, `RECOVERED`.


## Waiting on external CI

An existing GitHub Actions run in `queued`, `waiting`, `pending`, `requested`, or `in_progress` state is not itself a failure.

For every registered managed project:

1. bind the wait to the exact GitHub Actions run IDs that satisfy the task's required CI;
2. classify the state as `WAITING_EXTERNAL_CI` only while at least one bound run is still active;
3. do not dispatch or retry the same workflow while any bound run is active;
4. re-read those exact run IDs from GitHub no more frequently than the canonical bounded polling cadence unless new evidence arrives;
5. if an active run has not updated beyond the profile's stale threshold, classify it as `INVESTIGATE_STALE_CI` and inspect the existing run/jobs first;
6. if every bound run is terminal but the stored/control state still says `WAITING_EXTERNAL_CI`, classify `STALE_WAIT_STATE`; all-success routes immediately to Supervisor audit/validate/continue, while any failure/cancellation/timeout routes to Recovery;
7. on session resume after interruption, re-read the bound run IDs before any new dispatch. Never use a stale chat/UI spinner as proof that CI is still active.

Use a default 5-minute polling cadence and a 60-minute stale threshold unless a stricter canonical project rule applies. A long external CI job inside that window remains normal external work, not a loop. A completed external CI run must never leave the control plane parked indefinitely in `WAITING_EXTERNAL_CI`.

For registered managed-project v2 tasks, append-only recovery events are authoritative. New mutable v1 checkpoints must not be used as the source of retry counters; a checkpoint may only summarize legacy state.

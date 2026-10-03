# Recovery protocol

Classify failures as transient, ambiguous-write, permanent/configuration, loop/no-progress, or human-gated.

Transient: retry at most 3 total attempts for the same action fingerprint and re-read durable state whenever a mutation may have occurred.

Ambiguous write: never repeat until the source of truth proves the write did not happen. Inspect branches, commits, PRs, comments, merge state, workflow runs, or exact file content.

Permanent/configuration: do not blind-retry. Inspect arguments, permissions, repository/ref existence, and tool constraints.

Loop/no-progress: fingerprint `task + target + intended action + observed result`. After 2 identical failures, reconstruct/replan. After 3 no-progress iterations overall, stop the strategy.

Checkpoint: persist `.project-leader/checkpoints/<task-id>.json` when retry/no-progress state must survive interruption. Restore it before any further retry decision.

Resume: reconstruct default branch, task branch, PRs, task-related commits, checkpoint state, and CI/workflow state; determine the last durable completed step; verify ambiguous writes; continue from the first incomplete step.

Never automatically cross merge-to-main, release, production deploy, destructive data, repository/history deletion, production-secret, irreversible infrastructure, or paid-service gates without explicit authorization.


V2 recovery: use the append-only hash-chained journal under `.project-leader/recovery-events/<task-id>/` as the authoritative retry history. Commit `FAILURE_OBSERVED` and matching `RETRY_AUTHORIZED` before the next certifying execution, then run required CI on a descendant SHA containing those events. An old-SHA GitHub rerun cannot provide terminal structural certification. Commit `RECOVERED` after success as a descendant of the certified implementation SHA. Retroactive or structurally disconnected retry authorization is invalid, and an event file must never be rewritten. A checkpoint cannot reset the retry budget.

Legacy checkpoint liveness: a v1 checkpoint whose stored status is `ACTIVE` is actionable only with corroborating live branch, open PR, or active-CI evidence. If a terminal result exists or no live workstream exists, classify `STALE_LEGACY_CHECKPOINT` and preserve the snapshot without resuming its stale next step.

CI dispatch deduplication: before explicit dispatch/rerun, query the exact workflow name + target SHA + event context. Reuse active/successful exact matches; route terminal non-success to Recovery; create a new run only when no exact match exists.

External CI wait: queued/waiting/pending/requested/in_progress GitHub Actions are `WAITING_EXTERNAL_CI`, not failures. Bind the wait to exact run IDs and never dispatch a duplicate while any bound run is active. If a fresh read finds every bound run terminal while the control state still says waiting, classify `STALE_WAIT_STATE`: success returns to Supervisor continuation and failure/cancellation/timeout enters Recovery. After interruption/resume, reconcile those live run IDs before any new dispatch.

Evidence-only descendant CI: a failed automatic run on a permitted post-implementation evidence-only descendant is not task-certifying CI and must not by itself open another task Recovery generation. If branch protection/rulesets require current-head checks, handle that run as merge-governance evidence without moving the certifying implementation SHA. If interruption occurred before exact wait IDs were captured, reconstruct the existing run set from the live task, certifying SHA, PR/head and workflow contexts before dispatch.

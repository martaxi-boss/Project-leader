# Recovery protocol

Classify failures as transient, ambiguous-write, permanent/configuration, loop/no-progress, or authority/manual-boundary. An action name is not a Human Gate by itself.

For transient failures, retry at most 3 total attempts for the same action fingerprint and re-read durable state between attempts when a mutation may have occurred.

For ambiguous writes, never repeat the write until GitHub proves it did not happen. Inspect branches, commits, PRs, comments, merge state, workflow runs, or exact file content as appropriate.

For permanent/configuration failures, do not blind-retry. Inspect arguments, permissions, repository/ref existence, and tool constraints.

For loop/no-progress, fingerprint `task + target + intended action + observed result`. After 2 identical failures, reconstruct/replan. After 3 no-progress iterations overall, stop that strategy and return to Supervisor. Report `HUMAN_GATE` only if standing-authority resolution proves `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.

For legacy v1 tasks, persist `.project-leader/checkpoints/<task-id>.json` when retry/no-progress counters or strategy generation must survive interruption. For v2, use the append-only recovery journal instead. A legacy checkpoint marked `ACTIVE` is not live-state proof by itself: corroborate it with a current branch, open PR, or active CI. Without corroboration, or when a terminal result exists, classify `STALE_LEGACY_CHECKPOINT` and preserve it only as historical evidence.

After interruption, reconstruct default branch, task branch, PRs, task-related commits, v2 recovery journal (or legacy v1 checkpoint), and CI/workflow state; determine the last durable completed step; verify ambiguous writes; then continue from the first incomplete step.

Never self-authorize a consequential transition or bypass its evidence. After recovery, return exact durable state to Supervisor. If the effect is canonically covered, executable, and validated, Supervisor may authorize the exact transition through `STANDING_OWNER_GRANT`; otherwise continue remediation or emit a genuine Human Gate only for exclusive human intervention/new uncovered material decision.

Standing authority is preserved across recovery: technical failures, retries, stale waits, unsatisfied controls, and ambiguous writes are recovery/remediation, not new Owner-permission events. Recovery keeps one mutable target repository per task and never expands scope. Read `projects/standing-authority.json` before routing a recovered consequential next step.

A ChatGPT-wide outage cannot be repaired from inside another ChatGPT agent while the platform itself is unavailable. Resume from GitHub when service returns.


For Task Authorization v2, the append-only journal under `.project-leader/recovery-events/<task-id>/` is authoritative. Mutable checkpoints are legacy summaries only and cannot reset attempt/no-progress counters. Persist `FAILURE_OBSERVED` after classifying a retryable failure, `RETRY_AUTHORIZED` before the next dispatch/rerun, `REPLAN` before changing strategy generation, and `RECOVERED` after success. Do not certify a retry from chat memory alone when these durable events are missing.

Terminal certification must fail when required Recovery evidence is absent or causally invalid. A retroactive event is invalid. A recovery journal containing `RETRY_AUTHORIZED` triggers structural verification even when the fresh replacement CI run has `run_attempt=1`. The committed `FAILURE_OBSERVED`, `RETRY_AUTHORIZED`, and pre-retry `REPLAN` events must be ancestors of the CI-certified implementation SHA; terminal `RECOVERED` must be a descendant of that SHA on the final line. A live `run_attempt > 1` still requires the journal and timestamp checks, but an old-SHA rerun cannot satisfy terminal structural certification. Each recovery-event file must be created once and never rewritten.

Before explicit CI dispatch/rerun, deduplicate by exact workflow name + target SHA + event context: reuse active/successful exact matches, route terminal non-success to Recovery, and dispatch only if no exact match exists. Automatic runs in other event contexts may coexist and are reconciled as evidence.

An external GitHub Actions run that remains queued/waiting/pending/requested/in_progress is `WAITING_EXTERNAL_CI`, not a retryable failure. Bind the wait to exact run IDs, do not redispatch while any bound run is active, and re-read those IDs at a bounded cadence. If all bound runs are terminal while the control state still says waiting, classify `STALE_WAIT_STATE`: all-success routes to Supervisor audit/validate/continue and any failure/cancellation/timeout routes to Recovery. On session resume, reconcile live bound runs before any new dispatch; the chat/UI spinner is never authoritative.

Before routing a failed automatic run to task Recovery, classify whether its SHA is the certifying `implementation_head_sha` or only a permitted evidence-only descendant. Evidence-only descendant CI is non-certifying and does not itself reopen the task. If repository rules require checks on the current PR head, handle that run as a separate merge-governance condition without creating another evidence commit merely to obtain a new head. If interruption happened before exact run IDs were bound, reconstruct the existing run set from the live task, certifying SHA, required workflow names and PR/head before dispatching anything.

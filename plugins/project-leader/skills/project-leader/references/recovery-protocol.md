# Recovery protocol

Classify failures as transient, ambiguous-write, permanent/configuration, loop/no-progress, or human-gated.

For transient failures, retry at most 3 total attempts for the same action fingerprint and re-read durable state between attempts when a mutation may have occurred.

For ambiguous writes, never repeat the write until GitHub proves it did not happen. Inspect branches, commits, PRs, comments, merge state, workflow runs, or exact file content as appropriate.

For permanent/configuration failures, do not blind-retry. Inspect arguments, permissions, repository/ref existence, and tool constraints.

For loop/no-progress, fingerprint `task + target + intended action + observed result`. After 2 identical failures, reconstruct/replan. After 3 no-progress iterations overall, stop the strategy and report BLOCKED or HUMAN_GATE if a changed plan cannot proceed safely.

For legacy v1 tasks, persist `.project-leader/checkpoints/<task-id>.json` when retry/no-progress counters or strategy generation must survive interruption. For v2, use the append-only recovery journal instead.

After interruption, reconstruct default branch, task branch, PRs, task-related commits, v2 recovery journal (or legacy v1 checkpoint), and CI/workflow state; determine the last durable completed step; verify ambiguous writes; then continue from the first incomplete step.

Never use recovery to bypass merge, release, production deploy, destructive data, repository/history deletion, production-secret, irreversible infrastructure, or paid-service gates.

A ChatGPT-wide outage cannot be repaired from inside another ChatGPT agent while the platform itself is unavailable. Resume from GitHub when service returns.


For Task Authorization v2, the append-only journal under `.project-leader/recovery-events/<task-id>/` is authoritative. Mutable checkpoints are legacy summaries only and cannot reset attempt/no-progress counters. Persist `FAILURE_OBSERVED` after classifying a retryable failure, `RETRY_AUTHORIZED` before the next dispatch/rerun, `REPLAN` before changing strategy generation, and `RECOVERED` after success. Do not certify a retry from chat memory alone when these durable events are missing.

A required GitHub Actions run with live `run_attempt > 1` is objective evidence that retry recovery occurred. Terminal certification must fail unless the current head contains a valid append-only journal for that task with failure, retry authorization, and recovered evidence. The matching `RETRY_AUTHORIZED` event for that attempt must have been durably committed before the retry started; a retroactive event is invalid. Each recovery-event file must be created once and never rewritten.

An external GitHub Actions run that remains queued/waiting/pending/requested/in_progress is `WAITING_EXTERNAL_CI`, not a retryable failure. Do not redispatch it while active. Re-read at a bounded cadence; investigate the existing run first if it exceeds the canonical stale threshold.

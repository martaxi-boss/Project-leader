# Recovery protocol

Classify failures as transient, ambiguous-write, permanent/configuration, loop/no-progress, or human-gated.

For transient failures, retry at most 3 total attempts for the same action fingerprint and re-read durable state between attempts when a mutation may have occurred.

For ambiguous writes, never repeat the write until GitHub proves it did not happen. Inspect branches, commits, PRs, comments, merge state, workflow runs, or exact file content as appropriate.

For permanent/configuration failures, do not blind-retry. Inspect arguments, permissions, repository/ref existence, and tool constraints.

For loop/no-progress, fingerprint `task + target + intended action + observed result`. After 2 identical failures, reconstruct/replan. After 3 no-progress iterations overall, stop the strategy and report BLOCKED or HUMAN_GATE if a changed plan cannot proceed safely.

Persist `.project-leader/checkpoints/<task-id>.json` when retry/no-progress counters or strategy generation must survive interruption. Validate and restore it before deciding that another retry is allowed.

After interruption, reconstruct default branch, task branch, PRs, task-related commits, checkpoint state, and CI/workflow state; determine the last durable completed step; verify ambiguous writes; then continue from the first incomplete step.

Never use recovery to bypass merge, release, production deploy, destructive data, repository/history deletion, production-secret, irreversible infrastructure, or paid-service gates.

A ChatGPT-wide outage cannot be repaired from inside another ChatGPT agent while the platform itself is unavailable. Resume from GitHub when service returns.

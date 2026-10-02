# Recovery protocol

Classify failures as transient, ambiguous-write, permanent/configuration, loop/no-progress, or human-gated.

Transient: retry at most 3 total attempts for the same action fingerprint and re-read durable state whenever a mutation may have occurred.

Ambiguous write: never repeat until the source of truth proves the write did not happen. Inspect branches, commits, PRs, comments, merge state, workflow runs, or exact file content.

Permanent/configuration: do not blind-retry. Inspect arguments, permissions, repository/ref existence, and tool constraints.

Loop/no-progress: fingerprint `task + target + intended action + observed result`. After 2 identical failures, reconstruct/replan. After 3 no-progress iterations overall, stop the strategy.

Resume: reconstruct default branch, task branch, PRs, task-related commits, and CI/workflow state; determine the last durable completed step; verify ambiguous writes; continue from the first incomplete step.

Never automatically cross merge-to-main, release, production deploy, destructive data, repository/history deletion, production-secret, irreversible infrastructure, or paid-service gates without explicit authorization.

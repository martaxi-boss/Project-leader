---
name: recovery-guardian
description: Recovery controller for interrupted or failing software-project workflows. Use when the user explicitly selects or invokes Recovery Guardian, asks to recover a project after an error, loop, timeout, server-busy response, ambiguous write, interrupted execution, or wants Project Leader recovery diagnostics. Reconstruct durable state from GitHub, verify side effects before retrying writes, break no-progress loops, resume only within existing authorization, preserve standing authority, and stop only at genuine irreducible human gates.
---

# Recovery Guardian

Recover a registered project from interrupted or failing execution without duplicating writes, expanding scope, or bypassing consequential-transition controls.

## Activation

When invoked by itself, identify the active ChatGPT Project if possible and answer briefly that Recovery Guardian is active and ready.

If the Owner says `recover` or `continue after the error`, reconstruct the latest durable state before any mutation.

## Canonical sources

Use `martaxi-boss/Project-leader` as the control plane. Read live `RECOVERY_PROTOCOL.md`, `roles/RECOVERY_GUARDIAN.md`, `projects/standing-authority.json`, `projects/registry.yaml`, and the active project's applicable project record when present. Then inspect the target repository. Project isolation remains one mutable target repository per task.

## Workflow

1. Identify the active project and likely interrupted task.
2. Reconstruct default branch, task branch, PRs, relevant commits, CI/workflow state, and artifacts as applicable.
3. Look for and validate a durable Task Authorization Record at `.project-leader/tasks/<task-id>.json` when present, then compare it with current Owner instructions.
4. For v2 tasks, read and validate the append-only `.project-leader/recovery-events/<task-id>/` journal and restore retry/no-progress state from it. Use mutable checkpoints only as legacy summaries for v1 flows.
5. Classify the failure.
6. Follow `references/recovery-protocol.md`.
7. Verify every possibly-completed write before retrying it.
8. Retry only bounded transient failures.
9. Persist append-only recovery events for v2 retry/replan decisions; persist checkpoint changes only for legacy v1 continuity.
10. Replan after repeated no-progress instead of looping.
11. Before any CI dispatch/rerun during recovery, query exact workflow name + target SHA + event context. Reuse an active/successful exact run or route a terminal non-success through Recovery; create a new run only when no exact match exists.
12. If the interrupted state was `WAITING_EXTERNAL_CI`, re-read the exact bound GitHub run IDs before any dispatch. When every bound run is already terminal, classify `STALE_WAIT_STATE`; route all-success to Supervisor continuation and any failure/cancellation/timeout to Recovery without duplicating the run.
13. Before treating an automatic final-head run as task Recovery, classify its SHA. A permitted evidence-only descendant run is non-certifying; do not append task retry events or move `implementation_head_sha` solely because that run failed. If repository rules require live final-head checks, treat them as a separate merge-governance condition. If interruption occurred before run IDs were durably bound, reconstruct the existing exact runs from task/PR/head/workflow evidence before any dispatch.
14. Return recovered state to Supervisor logic for independent audit and standing-authority resolution of any consequential next action.

## Authorization

Recovery creates no new authority, but it must preserve authority that already exists.

Resume mutations when the current conversation or a compatible durable Task Authorization Record establishes that the work remains inside the same bounded scope. GitHub effects alone are not proof of the original mutation authority.

Technical errors, failed checks, unsatisfied controls, retries, stale waits, and ambiguous writes are remediation/recovery work, not Owner permission requests. After recovery, return exact durable evidence to Supervisor. Supervisor resolves any consequential next action through `projects/standing-authority.json`:
- covered + executable + controls satisfied -> exact `STANDING_OWNER_GRANT` transition and continue;
- covered but controls incomplete -> remediate/revalidate;
- `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION` -> `HUMAN_GATE`.

Never use recovery to widen scope, skip transition evidence, or bypass a genuine Human Gate.

## Platform outage limitation

Do not claim to monitor another ChatGPT chat while it is unreachable. A ChatGPT-wide or session-level outage cannot be repaired from inside another ChatGPT agent while the platform itself is unavailable.

Once ChatGPT is available again, reconstruct from GitHub and continue from the last verified step without requiring the Owner to reproduce repository history manually.

## Output

Report project/task reconstructed, last verified durable state, recovery action taken or reason no mutation was safe, and result: `RECOVERED`, `BLOCKED`, or `HUMAN_GATE`.

## V2 append-only recovery

For Task Authorization v2, read and validate the append-only recovery journal under `.project-leader/recovery-events/<task-id>/` before deciding whether another retry is allowed. The journal hash chain and monotonic counters are the authoritative retry history; a mutable checkpoint is only a convenience summary. For legacy v1 checkpoints, stored `ACTIVE` is not live-state proof: require corroborating current branch/PR/active-CI evidence, otherwise classify `STALE_LEGACY_CHECKPOINT` and preserve the file without resuming its stale `next_step`. Persist and commit `FAILURE_OBSERVED`, then `RETRY_AUTHORIZED`, before the next certifying execution. Run the replacement CI on a descendant SHA that already contains those commits; an old-SHA GitHub rerun is not terminal structural proof. Persist `RECOVERED` only after success, as a descendant of the CI-certified implementation SHA. Never reset a retry budget by rewriting a checkpoint or starting a new strategy generation without a valid `REPLAN` event.

# Project Leader runbook

## Architecture

Use **Project Leader** as the primary ChatGPT plugin.

Project Leader has four internal operating phases:
- Consultant
- Supervisor
- Builder
- Recovery Guardian

A separate **Recovery Guardian** plugin is also available for explicit recovery after an interrupted or failed session. It does not passively watch another ChatGPT chat.

## Normal invocation

`Open the relevant ChatGPT Project -> New chat -> @Project Leader -> wait for Owner instruction`

Calling `@Project Leader` only activates it. It does not automatically authorize an audit or construction work.

## Runtime loop

A CI-certified implementation head is the last material mutation point for that certification. Final evidence commits may follow only when they are task-local `.project-leader` result/recovery/transition-result metadata. Any other file change after `implementation_head_sha` is material drift: invalidate the old certification, choose the new implementation head, and run the required CI again before terminal acceptance.

External CI waits are transient control states, not stopping points. When Project Leader enters `WAITING_EXTERNAL_CI`, bind the exact run IDs and re-read them at the bounded cadence. If live GitHub state becomes terminal while the stored state still says waiting, classify `STALE_WAIT_STATE`: all-success returns immediately to Supervisor audit/validation/continuation; failure/cancellation/timeout routes to Recovery. After any interrupted/resumed Work session, re-read the bound runs before dispatching anything so completed work is never repeated merely because the UI remained on “processing”.

1. Consultant when analysis is needed.
2. Supervisor bounds authorized work and acceptance evidence.
3. Builder implements when authorized.
4. Supervisor audits actual evidence.
5. If remediation is local and within scope, loop to Builder.
6. If a transient failure, ambiguous write, interrupted response, or no-progress loop occurs, route automatically to Recovery Guardian.
7. Recovery Guardian verifies durable state, retries/replans within bounds, then returns to Supervisor.
8. If audit finds an in-scope defect, drift, stale evidence, overlap, or incomplete preparation, route it immediately to Builder/Recovery, correct it, validate it, and return to Supervisor. Do not stop merely to report a covered problem.
9. Before any Human Gate, exhaust convergence work: reconcile active workstreams, final-head scope/evidence/CI, durable recovery state, and every covered remediation.
10. Stop only when the requested task is complete, access/evidence is missing, the Owner changes direction, or no covered work remains and the next required action itself is a genuine Human Gate.

## Recovery rules

Follow `RECOVERY_PROTOCOL.md`.

Key requirements:
- verify a possibly-completed write before retrying it;
- maximum 3 attempts for the same transient action fingerprint;
- after 2 identical failures, reconstruct/replan;
- after 3 no-progress iterations, stop that strategy;
- on later resumption, rebuild state from GitHub instead of trusting an interrupted chat response;
- for v2 tasks, persist/re-read append-only `.project-leader/recovery-events/<task-id>/`; use mutable checkpoints only for legacy v1 continuity;
- never certify a consumed Human Gate without a durable exact-revision transition authorization/result pair; legacy gaps stay explicitly unverified.

## Platform outage

If ChatGPT itself is unavailable, no ChatGPT agent can continue at that instant. GitHub remains the durable state. When service returns, `@Project Leader` or `@Recovery Guardian` can reconstruct and resume without requiring the Owner to re-explain repository state.

## Human Gates

Owner approval is required by default for merge to main, release, production deployment, destructive data changes, repository/history deletion, production secret changes, irreversible infrastructure mutation, and paid service activation.

## Trust boundary

The roles are logical operating modes, not independent security principals. Consultant and Supervisor behave read-only; Builder writes only inside the authorized scope; Recovery Guardian only restores an already-authorized flow and never expands authority.

## V2 trusted execution path

For a v2 Project Leader task:

1. Reconstruct the live target repository, target base SHA, and the exact canonical Project Leader revision.
2. For Project Leader-local work, bind policy with `LOCAL_BASE_V1`. For a registered managed project, read its executable central policy from the canonical Project Leader revision and bind it with `CENTRAL_CONTROL_V1`.
3. Compile the task with the target base SHA plus the independent control repository/revision/policy path/profile/digest.
4. Require the task's mutation scope and allowed actions to remain inside that trusted policy ceiling.
5. Require policy-minimum Human Gates, validation, and CI.
6. Use append-only recovery events when retry/replan history exists.
7. Bind the Worker Result to the exact Task Authorization commit+SHA-256 and emit real GitHub Actions run IDs.
8. Verify authorization immutability, task/result compatibility, target CI evidence and implementation-head/final-head ancestry from trusted control-plane logic.

Repository branch protection/rulesets remain an external GitHub governance layer. The trusted workflow strengthens PR enforcement but does not make an unprotected `main` equivalent to a protected branch.

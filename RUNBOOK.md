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

Before explicitly dispatching or rerunning CI, deduplicate by exact workflow name + target SHA + event context. Reuse an existing active or successful exact-context run; route an exact-context terminal failure/cancellation/timeout to Recovery; dispatch only when no exact match exists. Automatic GitHub runs from different event contexts are coalesced as evidence and are not a reason to create more runs.

Before accepting CI for an implementation head, reject cherry-picked evidence: for every required workflow, inspect the latest same-SHA `push`, `pull_request`, and selected evidence context. Any latest active, failed, cancelled, or timed-out relevant context blocks terminal acceptance until that context becomes terminal-success or is otherwise legitimately superseded by a later successful run in the same context.

A CI-certified implementation head is the last material mutation point for that certification. Final evidence commits may follow only when they are task-local `.project-leader` result/recovery/transition-result metadata. Any other file change after `implementation_head_sha` is material drift: invalidate the old certification, choose the new implementation head, and run the required CI again before terminal acceptance.

Automatic CI triggered only because an allowed evidence-only descendant was pushed is not task-certifying CI. Do not reopen task Recovery or move `implementation_head_sha` solely because such an incidental descendant run is active or fails. If the repository's branch protection/ruleset explicitly requires checks on the current PR head, handle those runs as a separate merge-governance condition. They may delay Human-Gate readiness, but recovery must not create another evidence commit merely to satisfy a check on the prior evidence commit.

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
- for v2 tasks, persist/re-read append-only `.project-leader/recovery-events/<task-id>/`; use mutable checkpoints only for legacy v1 continuity. A certifiable retry must run on an implementation SHA that descends from the committed `FAILURE_OBSERVED` and `RETRY_AUTHORIZED` events; terminal `RECOVERED` is committed afterward. Do not use an old-SHA workflow rerun as final Recovery proof;
- never treat a legacy v1 checkpoint with stored `status=ACTIVE` as a live task by itself. Corroborate it with a current branch, open PR, or active CI. If a terminal result exists or no live workstream exists, classify `STALE_LEGACY_CHECKPOINT`, preserve the snapshot, and continue without reviving it;
- never certify a consumed Human Gate without a durable exact-revision transition authorization/result pair; legacy gaps stay explicitly unverified.

## Platform outage

If ChatGPT itself is unavailable, no ChatGPT agent can continue at that instant. GitHub remains the durable state. When service returns, `@Project Leader` or `@Recovery Guardian` can reconstruct and resume without requiring the Owner to re-explain repository state.

## Repository hygiene

Use `.github/workflows/repository-hygiene.yml` for branch cleanup. A non-`main` branch may be deleted automatically only when GitHub proves one of three bounded cases: (a) its tip is fully contained in canonical `main`; (b) it has no open pull request and every branch-specific final file state is byte-identical to canonical `main` (including removals that are also absent from `main`); or (c) canonical `main` contains a durable `CURRENT_OWNER_INSTRUCTION` transition authorization for action `delete_owner_authorized_superseded_non_main_branch_refs` whose target branch name and exact revision both match the live ref. Owner-authorized revision mismatches, renames, unsupported states, oversized/unavailable deltas, open-PR heads, and any unlisted/divergent content are preserved for explicit audit. The bounded sweep runs after same-repository merges, on manual dispatch, and after pushes to `main`, so temporary control/authorization refs disappear automatically once their evidence is canonical. Branch-ref deletion never rewrites commit history and must never target `main`.

## Standing authority and Human Gates

Load and validate `projects/standing-authority.json` at the start of consequential work and after resumption. It carries the Owner's standing autonomy grant across chats and recovery sessions.

A development-branch integration remains task-bounded: the task must include `merge_development_branch`, the live PR base must not be `main`, and no unrelated effect may be introduced.

A merge to `main`, release/publish, deploy, governance change, infrastructure/secret/data transition, or commercial transition is **not automatically a Human Gate** merely because of its action name or effect class. When the canonical project objective/decision already covers the effect and the system can technically perform it, Supervisor must bind the exact target, verify the required evidence, persist a `STANDING_OWNER_GRANT` transition authorization, execute, verify the result, and continue.

Stop for the Owner only when the next required step is either:
- `EXCLUSIVE_HUMAN_INTERVENTION`: technically unavailable to the current system/tools and must be performed personally by the Owner; or
- `NEW_UNCOVERED_MATERIAL_DECISION`: a material scope/architecture/strategy/trust/environment/commercial/irreversible-risk decision not already resolved canonically.

Do not turn a routine executable transition into a permission prompt.

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

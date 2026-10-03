# Project Leader final smoke tests

These tests describe the **current autonomous model**. Historical smoke behavior that expected routine Owner approval for merge/deploy/release is obsolete.

## Test 0 — Plugin discovery

Inside a ChatGPT Project, type:

`@pro`

Pass if **Project Leader** is selectable and **Recovery Guardian** is available when explicitly searched.

## Test 1 — Bare activation

Invoke:

`@Project Leader`

Pass if Project Leader activates and waits for the Owner's instruction without starting an audit or mutation on its own.

## Test 2 — Read-only reconstruction

Prompt:

`Faz uma auditoria completa deste projeto. Não alteres nada.`

Pass if Project Leader identifies the active target repository from current Project context/Owner instruction/live GitHub evidence, reconstructs current state, and performs no mutation.

## Test 3 — New-project bootstrap without registration

Use a software project that has never been added to the Project Leader repository.

Prompt:

`Reconstrói este projeto e continua dentro da arquitetura existente.`

Pass if Project Leader:

- does not require editing a central registry;
- reads the target project's own architecture/source/docs and live GitHub state;
- binds external work to the exact canonical Project Leader revision;
- uses an intentionally selected target-specific central policy when one exists, otherwise `control/generic-project-policy.json`;
- narrows the task to the target architecture rather than treating the generic policy as permission to change anything.

## Test 4 — Autonomous covered implementation and transition

Use a safe bounded project task whose architecture and objective already define the expected result.

Pass if the complete flow runs without routine Owner permission prompts:

`IDENTIFY -> RECONSTRUCT -> SUPERVISOR -> BUILDER -> CI/VALIDATION -> SUPERVISOR AUDIT -> CONSEQUENTIAL TRANSITION -> POST-TRANSITION AUDIT -> CONTINUE`

For a safe merge-to-`main` case, pass only if:

- exact PR/head/base are revalidated;
- required controls are green;
- an exact `STANDING_OWNER_GRANT` transition authorization is persisted;
- the merge is executed with exact-target safeguards;
- the durable result is re-read and audited;
- Project Leader does **not** stop merely to ask whether it may merge.

## Test 5 — Controls incomplete means remediation, not permission

Cause a safe CI/validation failure inside a covered task.

Pass if Project Leader routes to Builder/Recovery, fixes/replans/revalidates, and continues. Fail if it asks the Owner for permission merely because a check failed.

## Test 6 — Genuine manual Human Gate

Create a case whose next irreducible step cannot technically be performed with available tools, such as a physical-device test, unavailable UI-only action, MFA/physical confirmation, or Owner-only input.

Pass if Project Leader stops with:

`EXCLUSIVE_HUMAN_INTERVENTION`

and asks only for that concrete manual action.

## Test 7 — Genuine new-decision Human Gate

Create a case where continuing would require a material product/scope/architecture/strategy/trust/commercial decision not already resolved by the project.

Pass if Project Leader stops with:

`NEW_UNCOVERED_MATERIAL_DECISION`

and presents only the unresolved decision. Fail if it silently invents the decision.

## Test 8 — Ambiguous-write recovery

During a safe mutation, simulate a lost/errored response after a potentially completed write.

Pass if Recovery Guardian queries durable GitHub state before retry and never duplicates a completed effect.

## Test 9 — Loop breaker

Cause the same safe technical failure repeatedly.

Pass if retries remain bounded, repeated identical failure triggers reconstruction/replan, and the strategy is abandoned after the no-progress ceiling instead of looping indefinitely.

## Test 10 — Interrupted-session recovery

Stop a safe flow after at least one durable GitHub change. In a new session invoke:

`@Recovery Guardian`

then:

`Recupera e continua a partir do último estado verificável.`

Pass if it reconstructs task/branch/PR/commit/CI state from GitHub, preserves existing standing authority, and continues without asking the Owner to restate repository history or routine permissions.

## Test 11 — Evidence-only descendant CI

Certify an implementation head, then append only permitted Project Leader evidence metadata.

Pass if automatic CI on that evidence-only descendant is non-certifying and does not reopen task Recovery or create an evidence -> CI -> recovery -> evidence loop. If repository governance requires live final-head checks, treat them as merge-governance evidence only.

## Test 12 — Project isolation

While Project Leader is operating on project A, expose project B as reference context.

Pass if mutable actions remain restricted to project A. Project B may be read for context but is never mutated without its own target task/authority.

## Test 13 — Legacy isolation

Keep historical v1/v2 Project Leader records available for audit.

Pass if current runtime:

- never generates legacy `human_gates` fields;
- never depends on removed central project registry/profile files;
- never treats stale legacy checkpoints as live work without corroboration;
- can still validate historical records through archived schemas.

## Test 14 — Immutable authorization

For a new mutation-capable task, pass only if Task Authorization is persisted before substantive implementation, never rewritten afterwards, and Worker Result binds the exact authorization commit and digest.

## Test 15 — Package/runtime identity

Pass if the packaged Project Leader and Recovery Guardian versions match repository manifests, packaging is byte-reproducible, and installable ZIPs contain the current skills rather than obsolete runtime text.

## Test 16 — Active Work external-CI liveness

Start a covered task with a required GitHub Actions run that is initially `in_progress`, then let that exact bound run become terminal-success while the same Work execution still exists.

Pass only if Project Leader:

- represents the wait as `WAITING_EXTERNAL_CI` data, not as a passive UI/spinner wait;
- re-reads the exact bound run IDs at the bounded cadence without dispatching duplicates;
- routes terminal-success immediately through `STALE_WAIT_STATE -> AUDIT_CONTINUE` and continues the project in the same live execution;
- after two polling intervals without control-plane progress, enters `LIVENESS_RECONCILE_REQUIRED`, reconstructs task/PR/head/run state, and re-polls before any further wait or Human Gate;
- never treats the reconstruction itself as a CI retry or Owner permission request.

A fully frozen/unavailable ChatGPT Work process is outside the in-process guarantee; on the next activation, pass only if GitHub is reconstructed first and already-completed CI is not repeated.

## Test 17 — Forced Operational Access Discovery

Use project A with a task that needs read-only evidence from a server. Make the current Work session lack direct SSH. Provide an adjacent operations repository B, reasonably discoverable from the same Owner/project context, whose existing GitHub Actions history proves a workflow can reach that server through SSH.

Pass only if Project Leader:

- does not treat "this session has no SSH" as proof that access is unavailable;
- inspects direct session capabilities and project-A automation first, then discovers repository B read-only without violating project isolation;
- inspects existing workflow/run evidence and identifies the proven operational channel without reading or exposing secret values;
- uses the channel directly when no mutation is needed, or, when repository-B mutation is necessary and covered, creates a separate bounded operations task for B and later returns to project A;
- resolves standing/derived authority before asking the Owner if the cross-repository operation is not yet clearly covered;
- emits an access Human Gate only after all required discovery surfaces are exhausted and the state is `ACCESS_PATH_UNAVAILABLE`.

Fail if Project Leader asks the Owner to copy commands into a VPS merely because the current Work session lacks a direct SSH tool while a reasonably discoverable operational automation path exists.

## Final acceptance

This section is closed only when:

- all automated contract/validation/package checks are green on the exact implementation head;
- these smoke contracts are represented by automated tests wherever mechanically testable;
- no active runtime file still requires a central target-project registry or routine Owner approval by action name;
- no obsolete superseded branch is left as an active workstream;
- `main` post-merge is independently re-audited.

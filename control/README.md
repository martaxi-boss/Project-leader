# Durable Project Leader control records

Project Leader uses machine-readable records to bind task authority, execution evidence, consequential transitions, and recovery state.

These records preserve continuity and auditability. They do not invent product scope, architecture, or new authority.

## Task Authorization

Canonical current schema:

`task-authorization.schema.json`

Supervisor compiles the bounded record from verified target state plus current/canonical authority. Builder persists it as the first task artifact in the target repository:

`.project-leader/tasks/<task-id>.json`

Current v2 records use:

- `transition_controls` for consequential effects that require separate authority/evidence resolution;
- `required_validation` for acceptance checks;
- `required_ci` for applicable named workflows; this list may be empty when the target project has no applicable automated CI;
- `IMMUTABLE_AUTHORIZATION_V1` plus exact authorization commit/digest binding;
- `APPEND_ONLY_V1` recovery history.

Historical `human_gates` fields are compatibility-only evidence. The current runtime must not generate them.

A Task Authorization record never widens the project architecture or current Owner instruction. It contains no credentials, secrets, private conversation text, or unrelated project information.

## Worker Result

Canonical schema:

`worker-result.schema.json`

Builder emits one result for a mutation-capable task and, when target policy permits, persists it at:

`.project-leader/results/<task-id>.json`

`implementation_head_sha` identifies the material implementation state being certified. Evidence-only result/recovery/transition commits may follow it without becoming a new implementation head.

Worker Result is an audit index, not proof. Supervisor independently verifies refs, commits, diffs, PR state, CI, artifacts, and material non-effects.

`TERMINAL_SUCCESS` requires positive validation. Every task-required validation must be `PASS`; every task-required CI workflow must be represented by successful live GitHub run evidence. When `required_ci` is empty, positive validation/evidence remains mandatory.

## Consequential transition authorization/result

Canonical schemas:

- `transition-authorization.schema.json`
- `transition-result.schema.json`

A consequential transition such as an exact merge, deploy, release, governance change, infrastructure/secret/data transition, or commercial activation is outside the ordinary Builder implementation step.

Before the effect, Supervisor persists:

`.project-leader/transitions/<transition-id>.authorization.json`

When the standing-authority resolver proves that the canonical project already covers the effect and the system can execute it, the transition authority source may be:

`STANDING_OWNER_GRANT`

After the effect, persist:

`.project-leader/transitions/<transition-id>.result.json`

A `SUCCESS` transition result without matching prior authorization is invalid.

Historical observed effects without durable authorization stay `HISTORICAL_OBSERVED`; never fabricate retroactive approval.

## Human Gate

`HUMAN_GATE` is a runtime decision, not a synonym for a merge/deploy/release action.

It is valid only when the next irreducible step is:

- `EXCLUSIVE_HUMAN_INTERVENTION`; or
- `NEW_UNCOVERED_MATERIAL_DECISION`.

Covered technical failures, incomplete checks, CI failures, retries, recovery, or executable consequential transitions are not Owner-permission events.

## External target-project policy

Project Leader does not require a central registry of projects.

For external target repositories, use `CENTRAL_CONTROL_V1` bound to the exact canonical Project Leader revision.

If an intentionally maintained target-specific central policy is explicitly selected, bind it. Otherwise use:

`generic-project-policy.json`

The generic policy is only a safety ceiling. Supervisor must still reconstruct the target project's architecture and narrow every task's mutation scope and actions accordingly.

## Mutation-scope enforcement

Use:

`python control/validate_records.py scope <task-path> <changed-file> [<changed-file> ...]`

Every changed file must match the Task Authorization `mutation_scope`.

## Recovery

Current mutation-capable v2 tasks use append-only recovery events:

`.project-leader/recovery-events/<task-id>/`

Validate the journal with:

`python control/validate_records.py recovery-journal <event-1> <event-2> ...`

The journal is hash chained and monotonic so retry/no-progress history cannot be erased.

Mutable checkpoints remain only for historical/legacy continuity. A stored legacy `ACTIVE` checkpoint is not current-state proof without live branch/PR/CI corroboration.

## Trust model

`control/trusted_gate.py` evaluates untrusted task data against policy loaded from trusted base/control-plane state.

The `pull_request_target` trusted workflow never executes PR-head control code.

For external targets, target base SHA and canonical control-policy revision are independent states.

Required CI claims are verified against live GitHub data by exact workflow/run/SHA evidence.

## Historical compatibility

Archived v1 schemas remain because historical records are part of the audit trail:

- `task-authorization.v1.schema.json`
- `worker-result.v1.schema.json`

They are not templates for new work.

Historical v2 records that used old `human_gates` terminology remain readable for audit, while current runtime records use `transition_controls`.

## Validation commands

Examples:

`python control/validate_records.py task <task-path>`

`python control/validate_records.py result <result-path>`

`python control/validate_records.py pair <task-path> <result-path>`

`python control/validate_records.py recovery-journal <event-1> <event-2> ...`

`python control/validate_records.py transition-auth <authorization-path>`

`python control/validate_records.py transition-result <result-path>`

`python control/validate_records.py transition-pair <authorization-path> <result-path>`

GitHub Actions execute positive and negative contract tests on pull requests and pushes to `main`.

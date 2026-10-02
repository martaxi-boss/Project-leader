# Durable control records

Project Leader uses two machine-readable record types for mutation-capable tasks.

## Task Authorization Record

Canonical schema: `task-authorization.schema.json`.

Supervisor defines the record from the current Owner authorization and verified starting state. Builder persists it as the first task artifact in the **target repository**:

`.project-leader/tasks/<task-id>.json`

The record is continuity evidence only. It cannot grant itself authority, widen scope, override a later Owner instruction, cross a Human Gate, or prove that an unrecorded historical mutation was authorized.

Do not store credentials, secrets, private conversation text, personal data, or unrelated project information in the record.

## Worker Result

Canonical schema: `worker-result.schema.json`.

Builder emits one result at the end of a mutation-capable task and, when repository policy permits, persists it in the target repository:

`.project-leader/results/<task-id>.json`

`implementation_head_sha` identifies the implementation state being reported. The result record itself may be committed afterwards, so the result-file commit does not need to equal the implementation SHA.

Worker Result is an audit index, not proof. Supervisor still verifies GitHub refs, commits, diffs, PRs, CI, artifacts, and prohibited non-effects independently.

Optional history fields `recorded_at`, `state_observed_at`, `superseded_by`, and `post_transition_record` let future records express that an immutable historical result was later superseded or followed by a gated transition without rewriting the original record.

## Validation

The stdlib-only validator now applies every JSON Schema constraint used by the canonical schemas and rejects schema keywords it does not understand, preventing silent under-validation.

Validate one task:

`python control/validate_records.py task <task-path>`

Validate one result:

`python control/validate_records.py result <result-path>`

Validate task/result compatibility:

`python control/validate_records.py pair <task-path> <result-path>`

Pair validation binds task ID, repository, effect class, task branch, authorization-record path, and PR number when the task itself binds a PR. A TERMINAL_SUCCESS result also rejects failed validation and failed/pending CI.

GitHub Actions run positive and negative contract tests on pull requests and pushes to `main`.

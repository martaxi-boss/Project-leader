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

## Validation

The stdlib-only validator supports the core invariants without external dependencies:

`python control/validate_records.py task <path>`

`python control/validate_records.py result <path>`

GitHub Actions run the control-record tests on pull requests and pushes to `main`.

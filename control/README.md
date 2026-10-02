# Durable control records

Project Leader uses machine-readable records to bind authorization, execution evidence, Human-Gate transitions, and recovery state.

## Task Authorization Record

Canonical schema: `task-authorization.schema.json`.

Supervisor defines the record from the current Owner authorization and verified starting state. Builder persists it as the first task artifact in the **target repository**:

`.project-leader/tasks/<task-id>.json`

The record is continuity evidence only. It cannot grant itself authority, widen scope, override a later Owner instruction, cross a Human Gate, or prove that an unrecorded historical mutation was authorized.

Optional `required_validation` and `required_ci` fields make acceptance gates machine-enforceable. When present, a `TERMINAL_SUCCESS` Worker Result must contain those validation names as `PASS` and those CI names as `SUCCESS`.

Do not store credentials, secrets, private conversation text, personal data, or unrelated project information in the record.

## Worker Result

Canonical schema: `worker-result.schema.json`.

Builder emits one result at the end of a mutation-capable task and, when repository policy permits, persists it in the target repository:

`.project-leader/results/<task-id>.json`

`implementation_head_sha` identifies the implementation state being reported. The result record itself may be committed afterwards, so the result-file commit does not need to equal the implementation SHA.

Worker Result is an audit index, not proof. Supervisor still verifies GitHub refs, commits, diffs, PRs, CI, artifacts, and prohibited non-effects independently.

A `TERMINAL_SUCCESS` result requires non-empty positive validation. `SKIPPED` needs explicit evidence/justification and never satisfies a required validation gate. Required CI is enforced by task/result pair validation.

## Mutation-scope enforcement

Use:

`python control/validate_records.py scope <task-path> <changed-file> [<changed-file> ...]`

Every changed file must match at least one `mutation_scope` glob from the Task Authorization Record. Pull-request CI computes the real Git diff and fails closed on any out-of-scope file.

## Recovery Checkpoint

Canonical schema: `recovery-checkpoint.schema.json`.

Persist active recovery state at:

`.project-leader/checkpoints/<task-id>.json`

The checkpoint records the last durable step, action fingerprint, attempt counters, no-progress count, strategy generation, last error, and next step. It contains no private conversation text and never creates authority.

The validator enforces the protocol ceilings: no more than 3 attempts for one fingerprint, no more than 2 identical failures before replan, and no more than 3 no-progress iterations.

## Human-Gate Transition Authorization and Result

Canonical schemas:

- `transition-authorization.schema.json`
- `transition-result.schema.json`

For a Human Gate such as an authorized merge, persist an exact-revision authorization before the effect:

`.project-leader/transitions/<transition-id>.authorization.json`

After the effect, persist:

`.project-leader/transitions/<transition-id>.result.json`

A `SUCCESS` transition result is invalid without the matching durable authorization record. For legacy transitions whose effect is visible but whose authorization was not durably recorded, use `HISTORICAL_OBSERVED` with `authorization_record: null` and an explicit residual authorization-evidence gap. Never invent retroactive approval.

## Validation

The stdlib-only validator applies every JSON Schema constraint used by the canonical schemas and rejects schema keywords it does not understand.

Examples:

`python control/validate_records.py task <task-path>`

`python control/validate_records.py result <result-path>`

`python control/validate_records.py pair <task-path> <result-path>`

`python control/validate_records.py checkpoint <checkpoint-path>`

`python control/validate_records.py transition-auth <authorization-path>`

`python control/validate_records.py transition-result <result-path>`

`python control/validate_records.py transition-pair <authorization-path> <result-path>`

GitHub Actions run positive and negative contract tests on pull requests and pushes to `main`.

## V2 trust model

Historical Task Authorization and Worker Result records remain schema v1 and validate against archived v1 schemas. New hardened tasks use schema v2.

Task Authorization v2 requires:
- non-empty required validation and CI lists;
- an exact base-policy binding: profile, policy path, base SHA, and SHA-256 of the exact policy bytes;
- append-only recovery mode.

Worker Result v2 requires a non-empty CI list and concrete run IDs. `control/verify_github_evidence.py` resolves those run IDs through GitHub and checks workflow name, repository, implementation SHA, completion, success, and ancestry to the current PR head.

`control/trusted_gate.py` evaluates untrusted task data against a policy loaded from the PR base. The trusted `pull_request_target` workflow checks out only that base, fetches task/result records from the PR head as data, and never executes head code.

For v2 recovery, use `control/recovery-event.schema.json` and validate the whole journal with:

`python control/validate_records.py recovery-journal <event-1> <event-2> ...`

The journal is contiguous and SHA-256 hash chained, so retry counters cannot be erased by rewriting a later checkpoint.

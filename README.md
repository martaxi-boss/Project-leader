# Project Leader

Project Leader is an independent GitHub-backed control project packaged as two ChatGPT plugins:

- **Project Leader** — the reusable project-control entry point.
- **Recovery Guardian** — the recovery controller for interrupted, ambiguous, or failing execution.

## Operating model

Inside any ChatGPT Project:

`@Project Leader`

A bare invocation only activates the skill and waits for the Owner's instruction.

When work is requested, Project Leader identifies the active target repository from Project context, Owner instruction, and live GitHub evidence. **No central project registration is required.** The target project's own architecture, engineering decisions, source, tests, CI, and durable records define the work context.

Project Leader routes work through:

1. Consultant — read-only architecture/product/risk analysis.
2. Supervisor — reconstructs state, bounds work, authorizes exact transitions, and audits evidence.
3. Builder — implements only the bounded task or exact Supervisor transition.
4. Recovery Guardian — handles transient failures, ambiguous writes, interruptions, stale waits, retries, replans, and anti-loop recovery.

One mutable task targets one repository. Using Project Leader in one project never authorizes mutation of another project.

## Autonomous execution

The durable standing authority is:

`projects/standing-authority.json`

Within an already-defined project architecture/objective, Project Leader continues autonomously through implementation, tests, CI, PR management, remediation, recovery, and consequential transitions when:

- the canonical project state already covers the effect;
- the system has the tools/capability to execute it;
- required scope, exact-target, validation, CI/evidence, and Supervisor controls pass.

A merge to `main`, deploy, release, governance change, infrastructure/secret/data transition, or paid/commercial transition is **not** a Human Gate merely because of its action name.

Project Leader interrupts the Owner only for:

- `EXCLUSIVE_HUMAN_INTERVENTION` — the next irreducible step must actually be performed by a person because the available system/tools cannot perform it; or
- `NEW_UNCOVERED_MATERIAL_DECISION` — the next step requires a material product/scope/architecture/strategy/trust/commercial decision not already resolved by the project.

## New projects

Project Leader can operate on a new project without adding it to this repository.

For external target-project work:

- identify the live target repository;
- reconstruct the target architecture and current GitHub state;
- use an intentionally selected target-specific central policy when one exists;
- otherwise use `control/generic-project-policy.json`;
- narrow every task to the exact project architecture and mutation scope;
- discover applicable target CI from live repository state;
- never invent architecture or expand scope merely because a generic policy exists.

## Durable recovery

GitHub is the durable source of truth for branches, commits, PRs, CI, artifacts, and Project Leader task/recovery records.

A possibly-completed write is always verified before retrying. Recovery is bounded: repeated identical failures cause reconstruction/replan, no-progress loops are broken, active external CI is not duplicated, and resumed sessions reconstruct from durable GitHub state.

A ChatGPT-wide outage cannot be repaired while the service itself is unavailable. When service returns, Project Leader or Recovery Guardian reconstructs and continues from the last verified durable step.

## Control-plane source of truth

- `PROJECT_LEADER.md`
- `RUNBOOK.md`
- `RECOVERY_PROTOCOL.md`
- `projects/standing-authority.json`
- `control/generic-project-policy.json`
- `roles/CONSULTANT.md`
- `roles/SUPERVISOR.md`
- `roles/BUILDER.md`
- `roles/RECOVERY_GUARDIAN.md`
- `plugins/project-leader/skills/project-leader/SKILL.md`

Project-specific architecture remains in the target project/repository. Project Leader does not keep a central registry of target projects.

## Installation and packaging

The direct plugin-upload path is documented in `PLUGIN_SETUP.md`.

Fresh installable artifacts are built by:

`.github/workflows/package-plugins.yml`

Marketplace metadata:

`.agents/plugins/marketplace.json`

Both plugins use the OpenAI GitHub connector.

## Historical compatibility

Historical Project Leader task/result/transition records and archived schema versions remain only to preserve auditability. They do not define current runtime behavior.

Current runtime records use consequential **transition controls**, standing authority, immutable task authorization, append-only recovery history, and live GitHub evidence.

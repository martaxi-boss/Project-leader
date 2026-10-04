# Project Leader

GitHub-backed software-project coordination, packaged as two ChatGPT plugins:

- **Project Leader** — the single entry point for project work.
- **Recovery Guardian** — recovery after interrupted or failing execution.

Project Leader is an independent control project. External projects keep their architecture, implementation, credentials, CI and durable state in their own repositories. Every mutable task targets one repository.

## Use

`Open the relevant ChatGPT Project -> New chat -> @Project Leader`

Invocation activates the controller. The Owner then gives the concrete instruction to audit, build, fix, recover or continue.

Project Leader reconstructs live GitHub state, routes through Consultant, Supervisor and Builder, and independently audits actual evidence. Recovery Guardian enters when execution fails or a write has an uncertain outcome.

Covered work follows `DETECT -> AUDIT -> CORRECT -> VALIDATE -> CONTINUE`. A failed check routes to bounded remediation, rather than a routine request for permission.

## Authority and transitions

`projects/standing-authority.json` defines the standing Owner autonomy rule. Consequential effects require exact-target Supervisor audit, successful required validation and CI, and durable transition authorization and result records.

A covered, executable and validated transition uses `STANDING_OWNER_GRANT` and continues automatically. Human interruption is reserved for `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`. Recovery preserves existing authority and never expands it.

External targets bootstrap from their own architecture and live repository state. Use an explicitly selected target policy when applicable; otherwise bind `control/generic-project-policy.json` and narrow each task to the authorized objective.

## Canonical contracts

- `PROJECT_LEADER.md` — operational contract.
- `RUNBOOK.md` — execution and validation flow.
- `RECOVERY_PROTOCOL.md` — bounded recovery and CI waiting.
- `roles/` — Consultant, Supervisor, Builder and Recovery Guardian responsibilities.
- `projects/standing-authority.json` — standing Owner authority.
- `projects/policies/project-leader.json` — this repository's policy ceiling.
- `control/generic-project-policy.json` — architecture-first external-target policy.
- `control/` — executable authorization, scope, integrity and evidence checks.
- `SMOKE_TESTS.md` — acceptance scenarios.

New tasks use v2 records, immutable authorization before implementation, exact policy binding and concrete CI evidence whenever required. Recovery events are append-only. Archived schemas remain available because durable historical audit records still require validation.

## Installation and packaging

See `PLUGIN_SETUP.md` for installation. `.github/workflows/package-plugins.yml` builds deterministic installable ZIPs and a supply-chain manifest.

- Project Leader: **0.6.3**.
- Recovery Guardian: **0.5.3**.
- Marketplace: `.agents/plugins/marketplace.json`.
- Plugin source: `plugins/project-leader/` and `plugins/recovery-guardian/`.

Both plugins use the OpenAI GitHub connector, limited to the repositories and actions authorized for the signed-in account.

## Continuity and repository hygiene

GitHub stores task authority, commits, PRs, CI, results and transition evidence. Verify a potentially completed write before repeating it. Reconstruct from the last verified durable state after an interruption.

Repository hygiene removes obsolete runtime/configuration dependencies and audited obsolete branch refs. Preserve useful audit evidence before deleting refs; never delete unique valuable history merely because a branch is old.

A ChatGPT-wide outage prevents execution while the service is unavailable. Resume by reconstructing GitHub state after service returns.

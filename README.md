# Project Leader

GitHub-backed control plane packaged as two ChatGPT plugins:

- **Project Leader** — the primary single entry point for software-project work.
- **Recovery Guardian** — an independent recovery controller for interrupted or failing execution.

## Intended use

`Open a ChatGPT Project -> New chat -> @Project Leader`

A bare invocation activates Project Leader and waits for the Owner's next instruction.

Project Leader internally routes work through four phases:

1. Consultant
2. Supervisor
3. Builder
4. Recovery Guardian

After Builder work, Supervisor independently audits evidence. If execution fails transiently, a write outcome is ambiguous, the response is interrupted, or progress loops, Recovery Guardian automatically enters, verifies durable GitHub state, retries/replans safely, and returns to Supervisor.

The standalone `@Recovery Guardian` plugin is available for explicit recovery after an interrupted session.

## Durable recovery

GitHub is the durable source of truth for branches, commits, PRs, CI, and artifacts. A possibly-completed write is always verified before retrying. Repeated no-progress attempts are bounded by `RECOVERY_PROTOCOL.md`.

A ChatGPT-wide outage cannot be repaired by another ChatGPT agent while the service itself is unavailable. When service returns, Project Leader or Recovery Guardian reconstructs from GitHub and resumes from the last verified step.

## Control-plane source of truth

- `PROJECT_LEADER.md`
- `RUNBOOK.md`
- `RECOVERY_PROTOCOL.md`
- `roles/CONSULTANT.md`
- `roles/SUPERVISOR.md`
- `roles/BUILDER.md`
- `roles/RECOVERY_GUARDIAN.md`
- `projects/registry.yaml`
- project-specific files under `projects/`

## Plugin packaging

Marketplace:
`.agents/plugins/marketplace.json`

Plugins:
- `plugins/project-leader/`
- `plugins/recovery-guardian/`

Both require the OpenAI GitHub connector.

See `PLUGIN_SETUP.md` for the one-time workspace import/install.

## Registered test projects

- `martaxi-boss/pink-iptv`
- `martaxi-boss/fadego`
- `martaxi-boss/VCAM-PRO`

## Safety

Automatic inside an authorized bounded task: repository reads, analysis, branch/commit/PR work, CI inspection, in-scope remediation, and bounded recovery.

Human-gated by default unless explicitly authorized: merge to main, release/publication, production deployment, destructive data operations, repository/history deletion, production secret changes, irreversible infrastructure changes, and paid-service activation.

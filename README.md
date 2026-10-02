# Project Leader

Control plane for multiple software projects managed from a ChatGPT Business Workspace Agent.

## Goal

Use one Workspace Agent named **Project Leader** as the single entry point for project work. The agent follows three internal roles:

- **Consultant** — product, architecture, requirements, options, and risk analysis.
- **Supervisor** — reconstructs repository state, defines bounded work, audits diffs/CI, and enforces gates.
- **Builder** — implements approved work on branches, runs or triggers tests, and prepares pull requests.

The intended user experience is simple:

```text
Continue PINK IPTV.
Continue FADEGO.
Audit and continue VCAM-PRO.
```

The Project Leader selects the registered repository, reconstructs its live GitHub state, runs the Consultant -> Supervisor -> Builder -> Supervisor workflow, and continues until completion or a human gate.

## Registered test projects

- `martaxi-boss/pink-iptv`
- `martaxi-boss/fadego`
- `martaxi-boss/VCAM-PRO`

See `projects/registry.yaml`.

## Safety model

Automatic within an authorized task:

- read repository state
- analyze requirements and architecture
- create a working branch
- edit project files
- run/trigger CI
- inspect test and workflow results
- commit changes
- open/update a pull request
- request Builder remediation after failed audit

Human gate by default:

- merge to `main`
- release
- production deploy
- destructive data operations
- repository deletion
- secrets/credential changes
- irreversible infrastructure changes

## Important implementation note

Consultant, Supervisor, and Builder are **internal phases of one Workspace Agent**. This avoids manual prompt-copying between separate chats. Because they share the same connected GitHub app, role separation is enforced by instructions: Consultant and Supervisor behave read-only; Builder performs allowed writes.

## Source patterns

This repository adapts two official OpenAI Cookbook patterns:

1. ChatGPT Workspace Agents for repeatable end-to-end work.
2. Project-manager orchestration with specialist roles and gatekeeping between stages.

See `SOURCES.md` for the exact references.

## Setup

1. Create a ChatGPT Business Workspace Agent named **Project Leader**.
2. Give it GitHub access to the repositories you want it to manage.
3. Paste the contents of `AGENT_BUILDER_PROMPT.md` into the conversational Agent Builder.
4. Keep `PROJECT_LEADER.md`, `roles/`, and `projects/registry.yaml` as the control-plane source of truth.
5. Test with a low-risk request such as: `Audit PINK IPTV and tell me the next safe task. Do not write yet.`

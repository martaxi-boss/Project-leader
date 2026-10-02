# Project Leader

GitHub-backed control plane packaged as a ChatGPT plugin named **Project Leader**.

## Goal

Use one invokable Project Leader as the single entry point for software-project work. The Owner should not have to copy prompts between separate Consultant, Supervisor, and Builder chats.

The intended flow is:

```text
Open a ChatGPT Project -> New chat -> @Project Leader
```

A bare invocation activates Project Leader and waits for the Owner's next instruction. It does **not** automatically audit or continue the project.

Example follow-up commands:

```text
Faz uma auditoria completa deste projeto.
Continua a construção a partir do estado atual.
Vê o PR aberto e diz-me o que falta.
Corrige o problema encontrado na auditoria.
```

## Architecture

Project Leader is one controller with three internal operating phases:

- **Consultant** — product, architecture, requirements, reuse, tradeoffs, and risk analysis. Read-only.
- **Supervisor** — reconstructs live state, bounds work, audits diffs/CI/evidence, and enforces gates. Read-only for implementation.
- **Builder** — implements only authorized bounded work, tests it, commits, and prepares PRs.

After Builder work, control returns to Supervisor audit. In-scope remediation can continue automatically.

The live control-plane source of truth is:

- `PROJECT_LEADER.md`
- `RUNBOOK.md`
- `roles/CONSULTANT.md`
- `roles/SUPERVISOR.md`
- `roles/BUILDER.md`
- `projects/registry.yaml`
- project-specific files under `projects/`

## ChatGPT plugin packaging

The installable plugin lives at:

```text
plugins/project-leader/
```

The repository marketplace lives at:

```text
.agents/plugins/marketplace.json
```

The plugin requires the OpenAI GitHub connector and uses the live GitHub repositories as evidence.

See `PLUGIN_SETUP.md` for the one-time workspace import/install.

## Registered test projects

- `martaxi-boss/pink-iptv`
- `martaxi-boss/fadego`
- `martaxi-boss/VCAM-PRO`

See `projects/registry.yaml`.

## Safety model

Automatic within an authorized bounded task:

- read repository state;
- analyze requirements and architecture;
- create a working branch;
- edit project files;
- run or trigger CI;
- inspect tests and workflow results;
- commit changes;
- open or update a pull request;
- remediate failed audit findings inside the same authorized scope.

Human gate by default unless the current Owner instruction explicitly authorizes the exact action:

- merge to `main`;
- release/publication;
- production deployment;
- destructive data operations;
- repository/history deletion;
- production secret changes;
- irreversible infrastructure changes;
- paid-service activation.

## Legacy note

`AGENT_BUILDER_PROMPT.md` is retained as a historical/manual fallback. The preferred current architecture is the repository-backed ChatGPT plugin.

## Sources

See `SOURCES.md` for the OpenAI patterns and current plugin packaging references.

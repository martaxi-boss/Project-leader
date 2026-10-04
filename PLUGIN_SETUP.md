# Project Leader plugin setup

This repository contains two ChatGPT plugins:

- **Project Leader** — primary project controller.
- **Recovery Guardian** — independent recovery controller for interrupted/failed sessions.

Project Leader also uses the Recovery Guardian protocol internally, so normal work does not require manual role switching.

## Current canonical runtime

- Project Leader **0.6.5**.
- Recovery Guardian **0.5.3**.

Before consequential work, read the live `PROJECT_LEADER.md`, `RUNBOOK.md`, `RECOVERY_PROTOCOL.md`, role contracts and `projects/standing-authority.json` from canonical GitHub state. The active target's architecture and live repository state define its bounded task; external projects do not require central enrollment.

On each `@Project Leader` invocation, the Skill performs `CANONICAL_RUNTIME_BOOTSTRAP` when GitHub read access is available. If the installed/runtime copy lags canonical `main`, `RUNTIME_SYNC_STALE -> RUNTIME_CANONICAL_OVERRIDE_ACTIVE` keeps the invocation on the newest canonical contract without requiring another manual sync before work can continue.

The 0.6.5 runtime also applies `BOUNDED_STATE_PREFLIGHT` before potentially broad internal reconstruction/compare work and keeps repository hygiene non-blocking for ordinary managed-project execution.

Covered executable transitions continue through exact Supervisor authorization and validation under standing Owner authority. Human interruption is reserved for exclusive human intervention or a new uncovered material decision.

## Proven direct install path

The installation path verified in the current ChatGPT workspace is:

1. Open **Plugins**.
2. Press the **+** button beside plugin search.
3. Choose **Carregar plugin / Upload plugin**.
4. Select the installable ZIP:
   - `project-leader.zip`
   - `recovery-guardian.zip`
5. Wait for **Importação bem-sucedida / Import successful**.
6. Press **Ver plugin / View plugin**.
7. Press **Instalar plugin / Install plugin**.
8. Approve the GitHub dependency if prompted.

After installation, verify availability in a project chat by typing `@pro`. **Project Leader** should appear. **Recovery Guardian** should also be available when explicitly searched or selected.

## GitHub-built ZIP artifacts

The workflow `.github/workflows/package-plugins.yml` produces installable ZIP artifacts for both plugins on pull requests and pushes to `main`.

Each ZIP is built with the plugin manifest at the ZIP root, matching the direct upload format.

## Marketplace import alternative

Some workspace admin surfaces may expose marketplace import/sync. Where that UI is available, the repository marketplace is:

`https://github.com/martaxi-boss/Project-leader`

The marketplace manifest is `.agents/plugins/marketplace.json`.

If the current workspace UI does not expose marketplace import, use the proven direct ZIP upload path above instead.

## Normal use

Inside a ChatGPT Project:

`@Project Leader`

Then give the command, for example:

- `Faz uma auditoria completa deste projeto.`
- `Continua a construção a partir do estado atual.`
- `Vê o PR aberto e corrige o que faltar.`

Project Leader automatically routes through Consultant, Supervisor, Builder, and Recovery Guardian phases as needed.

## Manual recovery

After an interrupted session you may instead invoke:

`@Recovery Guardian`

Then:

`Recupera e continua a partir do último estado verificável.`

Recovery Guardian reconstructs from GitHub before repeating any write.

## Important limitation

Neither plugin can keep running inside ChatGPT while the ChatGPT service itself is unavailable, and Recovery Guardian cannot passively watch another dead chat. The resilience mechanism is durable-state recovery from GitHub after service returns.

## GitHub dependency

Both plugins reference the installed OpenAI GitHub connector. Access remains limited to the repositories and actions authorized for the signed-in account.

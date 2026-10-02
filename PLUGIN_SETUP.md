# Project Leader marketplace setup

This repository contains two ChatGPT plugins:

- **Project Leader** — primary project controller.
- **Recovery Guardian** — independent recovery controller for interrupted/failed sessions.

Project Leader also uses the Recovery Guardian protocol internally, so normal work does not require manual role switching.

## One-time workspace import

After this repository is on `main`:

1. Open **Workspace settings -> Plugins**.
2. Select **Add -> Import marketplace**.
3. Source: `https://github.com/martaxi-boss/Project-leader`
4. Leave **Path** empty.
5. Leave **Branch** empty to follow `main`.
6. Import the marketplace and authorize GitHub when prompted.
7. Open **Project Leader** and set installation policy to **Installed** for the intended role/users.
8. Open **Recovery Guardian** and set it to **Installed** if you want direct `@Recovery Guardian` access.
9. Confirm the required GitHub app is enabled and connected.

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

## Updates

The GitHub marketplace can sync future changes from this repository. Use **Sync now** in Workspace settings -> Plugins -> Marketplaces when you want an immediate refresh after a merged update.

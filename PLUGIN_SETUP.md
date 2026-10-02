# Project Leader plugin setup

This repository now contains a ChatGPT plugin named **Project Leader**.

## Goal

After the one-time workspace import/install, the normal mobile flow is:

```text
Open a ChatGPT Project -> New chat -> @Project Leader
```

A bare invocation only activates Project Leader and waits. The Owner then gives the command, for example:

```text
Faz uma auditoria completa deste projeto.
Continua a construção a partir do estado atual.
Vê o PR aberto e corrige o que faltar.
```

Project Leader then uses the current Project context and the GitHub control plane to route the work internally through Consultant, Supervisor, and Builder.

## One-time workspace import

After this plugin is on `main`:

1. Open **Workspace settings -> Plugins**.
2. Select **Add -> Import marketplace**.
3. Source: `https://github.com/martaxi-boss/Project-leader`
4. Leave **Path** empty.
5. Leave **Branch** empty to follow the default branch `main`.
6. Import the marketplace.
7. Open the imported **Project Leader** plugin and set its installation policy to **Installed** (or install it for the intended workspace role).
8. Confirm the required GitHub app is enabled and connected.

The marketplace manifest is at `.agents/plugins/marketplace.json`.
The plugin source is at `plugins/project-leader/`.

## GitHub dependency

The plugin references the OpenAI GitHub connector with app id:

```text
connector_76869538009648d5b282a4bb21c3d157
```

The connector remains subject to the workspace and GitHub permissions of the signed-in user.

## Update model

The GitHub marketplace can sync updates from this repository. Keep the plugin package and control-plane files in the same repository so role and registry changes can be reviewed and versioned together.

## Safety

Project Leader preserves the repository's Human Gates. Invocation is not authorization to merge, deploy, release, mutate production data, change secrets, perform irreversible infrastructure work, or spend money.

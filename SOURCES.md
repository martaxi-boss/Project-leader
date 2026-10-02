# Source patterns

This control plane is an adaptation, not a wholesale copy, of official OpenAI patterns and current plugin packaging documentation.

## ChatGPT plugin model

OpenAI Help Center:

- Plugins in ChatGPT
- Importing and syncing plugin marketplaces from GitHub

Relevant ideas:

- plugins can package reusable skills and connected apps;
- an installed plugin can be selected with an `@` mention where supported;
- workspace admins can import a plugin marketplace from a GitHub repository and keep it synchronized.

## Plugin packaging

OpenAI Developers:

- Package your plugin
- Build skills
- Upload and submit your plugin

Relevant ideas:

- a plugin can package one or more skills;
- repository marketplaces use `.agents/plugins/marketplace.json`;
- a plugin can reference an eligible existing app through `.app.json`;
- plugin display metadata can expose the human-facing name **Project Leader**.

## Project Manager orchestration pattern

OpenAI Cookbook:
`examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk.ipynb`

Repository:
`openai/openai-cookbook`

Relevant idea: a project manager receives the initial request, coordinates specialist roles, verifies required evidence, and enforces gatekeeping before moving to the next stage.

## Earlier Workspace Agent pattern

The repository originally adapted a ChatGPT Business Workspace Agent workflow. `AGENT_BUILDER_PROMPT.md` is retained as a manual fallback, but the preferred current distribution path is the ChatGPT plugin packaged in this repository.

## License note

The OpenAI Cookbook is MIT licensed. This repository keeps its own simplified instructions and workflow rather than importing the notebook implementation.

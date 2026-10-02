# Project Leader runbook

## Architecture

Use **one** ChatGPT Business Workspace Agent named **Project Leader**.

Do **not** create separate Workspace Agents for Consultant, Supervisor, or Builder. They are operating phases of Project Leader.

## Invocation examples

- `Continue PINK IPTV.`
- `Continue FADEGO.`
- `Audit and continue VCAM-PRO.`
- `What is blocking PINK IPTV?`

## Runtime loop

1. Resolve the project from `projects/registry.yaml`.
2. Read the project snapshot under `projects/*.md`.
3. Refresh live GitHub state before acting.
4. Consultant phase: analyze objective and next safe step.
5. Supervisor phase: define one bounded task and acceptance evidence.
6. Builder phase: implement only that task.
7. Supervisor audit: inspect diff/CI/artifacts.
8. If remediation is local and authorized, loop back to Builder.
9. Stop only for completion, missing essential access, conflict, or Human Gate.

## Human Gates

Owner approval is required by default for:
- merge to main;
- release;
- production deployment;
- destructive data changes;
- repository deletion;
- production secret changes;
- irreversible infrastructure mutation;
- paid service activation.

## Trust boundary

Consultant/Supervisor/Builder are logical roles inside one agent, not independent security principals. Therefore:
- Consultant and Supervisor must behave read-only;
- Builder may write only within the Supervisor-approved task;
- irreversible actions remain human-gated.

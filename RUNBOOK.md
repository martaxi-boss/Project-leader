# Project Leader runbook

## Architecture

Use **one** ChatGPT Business Workspace Agent named **Project Leader**.

Do **not** create separate Workspace Agents for Consultant, Supervisor, or Builder. They are operating phases of Project Leader.

## Normal invocation

The intended workflow is:

```text
Open the relevant ChatGPT Project
-> New chat inside that Project
-> @Project Leader
-> full project audit
-> automatic continuation
```

The Owner should not need to type a long instruction after `@Project Leader`.

## Startup audit

On every fresh invocation inside a Project:

1. infer the active project from the current ChatGPT Project context;
2. map it to its GitHub repository;
3. inspect relevant Project instructions/files/context;
4. refresh live GitHub state;
5. inspect default-branch HEAD, active branches, open PRs, recent commits, CI/workflows, logs/artifacts when relevant;
6. reconcile GitHub reality with prior project state;
7. identify unfinished work and the next safe task;
8. begin the execution loop automatically.

## Runtime loop

1. Consultant phase: analyze objective and next safe step.
2. Supervisor phase: define one bounded task and acceptance evidence.
3. Builder phase: implement only that task.
4. Supervisor audit: inspect diff/CI/artifacts.
5. If remediation is local and authorized, loop back to Builder.
6. If accepted, continue to the next safe unfinished task.
7. Stop only for completion, missing essential access, conflict, or Human Gate.

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

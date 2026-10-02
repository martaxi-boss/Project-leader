# Project Leader runbook

## Architecture

Use **Project Leader** as the primary ChatGPT plugin.

Project Leader has four internal operating phases:
- Consultant
- Supervisor
- Builder
- Recovery Guardian

A separate **Recovery Guardian** plugin is also available for explicit recovery after an interrupted or failed session. It does not passively watch another ChatGPT chat.

## Normal invocation

`Open the relevant ChatGPT Project -> New chat -> @Project Leader -> wait for Owner instruction`

Calling `@Project Leader` only activates it. It does not automatically authorize an audit or construction work.

## Runtime loop

1. Consultant when analysis is needed.
2. Supervisor bounds authorized work and acceptance evidence.
3. Builder implements when authorized.
4. Supervisor audits actual evidence.
5. If remediation is local and within scope, loop to Builder.
6. If a transient failure, ambiguous write, interrupted response, or no-progress loop occurs, route automatically to Recovery Guardian.
7. Recovery Guardian verifies durable state, retries/replans within bounds, then returns to Supervisor.
8. Stop only when the requested task is complete, a Human Gate is reached, access/evidence is missing, or the Owner changes direction.

## Recovery rules

Follow `RECOVERY_PROTOCOL.md`.

Key requirements:
- verify a possibly-completed write before retrying it;
- maximum 3 attempts for the same transient action fingerprint;
- after 2 identical failures, reconstruct/replan;
- after 3 no-progress iterations, stop that strategy;
- on later resumption, rebuild state from GitHub instead of trusting an interrupted chat response.

## Platform outage

If ChatGPT itself is unavailable, no ChatGPT agent can continue at that instant. GitHub remains the durable state. When service returns, `@Project Leader` or `@Recovery Guardian` can reconstruct and resume without requiring the Owner to re-explain repository state.

## Human Gates

Owner approval is required by default for merge to main, release, production deployment, destructive data changes, repository/history deletion, production secret changes, irreversible infrastructure mutation, and paid service activation.

## Trust boundary

The roles are logical operating modes, not independent security principals. Consultant and Supervisor behave read-only; Builder writes only inside the authorized scope; Recovery Guardian only restores an already-authorized flow and never expands authority.

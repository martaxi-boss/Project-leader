# Changelog

This file records consumer-visible Project Leader control/runtime changes. Exact implementation and CI evidence remain in Git history, pull requests, Task Authorization records, Worker Results and transition records.

## 0.7.0 / Recovery Guardian 0.6.0 — 2026-10-07

- Make `EXECUTION_FIRST_WITHIN_BOUNDS` and FAST_E1 the normal path for reversible covered work; remove authorization-only/task-result/handoff ceremony from ordinary E1.
- Add `PROGRESS_OVER_PROCESS`, `FUNCTIONAL_CONVERGENCE_FIRST`, `DIAGNOSIS_MUST_BUY_A_DECISION`, `REGRESSION_FIRST`, selective safe rollback, evidence reuse and progressive loading.
- Keep Consultant, Supervisor, Builder and Recovery Guardian as internal capabilities rather than a mandatory serialized chain; Recovery Guardian directly repairs covered faults.
- Preserve proportional durable controls for destructive/privileged/material architecture, release/deploy/production, permission/secrets/trust/governance, irreversible, ambiguous-write and continuity/audit-sensitive work.
- Add executable FAST_E1 vs DURABLE_CONTROL selection and tests for decision-buying diagnosis/regression handling.
- Close the stale-base gap even with GitHub ruleset strict-update disabled: a push to `main` invalidates prior `trusted-authorization` checks on every open PR head, forcing recertification against the new base.
- Align version identity to Project Leader 0.7.0 / Recovery Guardian 0.6.0 and retain continuous same-cycle hygiene.

### Included audit hardening carried forward from the prior unreleased state

- Tighten JSON/schema semantics so booleans cannot masquerade as numbers, anchored identifiers reject trailing data, and date-time fields use RFC3339 extended form.
- Reject partial/mixed fixed-vs-`ACTIVE_TARGET` project policy declarations.
- Protect root-level `secrets*` and nested `.env*` paths under the generic managed-project policy.
- Require the canonical standing-authority control set and distinct schema IDs for legacy versions.
- Reject malformed external-CI observations and helper booleans before using them as execution evidence.
- Add `control/runtime_execution.py` plus behavioral acceptance for bounded preflight, internal-stall detection, ambiguous-write reconciliation, restart deduplication, timeout handling and external-CI routing.
- Remove obsolete Recovery wording and tautological phrase-only assertions while retaining behavior-level tests.
- Add explicit source/provenance links, distribution-verification instructions and GitHub Actions event-policy readiness documentation.
- Record an observed ChatGPT host invocation of the Project Leader skill, including stale-loaded-copy reconciliation via canonical runtime override and the absence of a public global release identity in the available plugin-management surface.
- The repository Owner selected a proprietary / All Rights Reserved license; `LICENSE` now records that no general open-source reuse permission is granted and preserves third-party license obligations.

## 0.6.8 / Recovery Guardian 0.5.6 — 2026-10-06

- Simplified Project Leader execution around direct covered work, compact Recovery Guardian repair and continuous same-cycle hygiene.
- Added bounded state preflight and stale/live Work liveness reconciliation.
- Added pinned canonical runtime generation and stronger package provenance/confinement.
- Hardened trusted CI evidence, immutable authorization history, Recovery journal continuity and transition-failure evidence.

## Historical versions

Older durable records and legacy schemas remain in the repository for audit compatibility. Git history is authoritative for exact pre-0.6.8 changes.

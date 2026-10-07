---
name: recovery-guardian
description: Recovery controller for interrupted or failing software-project workflows. Use when the user explicitly selects or invokes Recovery Guardian, asks to recover a project after an error, loop, timeout, server-busy response, ambiguous write, interrupted execution, or wants Project Leader recovery diagnostics. Reconstruct durable state from GitHub, verify side effects before retrying writes, directly diagnose/correct/test covered recoverable E1 failures, apply related continuous hygiene, break blind-retry/no-progress loops, preserve standing authority, and stop only at genuine irreducible human gates.
---

# Recovery Guardian

Recover the active project from interrupted or failing execution without duplicating writes, expanding scope, or bypassing consequential-transition controls.

## Activation

When invoked by itself, identify the active ChatGPT Project if possible and answer briefly that Recovery Guardian is active and ready.

If the Owner says `recover` or `continue after the error`, reconstruct the latest durable state before any mutation.

## Canonical sources

Resolve any Owner interruption through live `control/standing_authority.py::resolve_next_action` and its input contract in `control/README.md`. Missing capability alone stays in discovery/remediation. Recompute operational/diagnostic closure from raw observations, require verified `convergence_complete` and exact `human_intervention` evidence, and exhaust covered work independent of the human step first. Evidenced physical/device interaction or Owner-held input may bypass operational discovery after automated prerequisites pass; the requested manual test's future result is not a prerequisite. New uncovered decisions are never implemented during convergence. If evidence remains unavailable, use bounded anti-loop recovery instead of fabricating a manual gate.

Use `martaxi-boss/Project-leader` as the control plane. Read live `RECOVERY_PROTOCOL.md`, `roles/RECOVERY_GUARDIAN.md`, and `projects/standing-authority.json`, then reconstruct the active target repository from durable task evidence, current Project context, current Owner instruction, and live GitHub state. No central project registry is required. Project isolation remains one mutable target repository per task.

## Workflow

1. Identify the active project/interrupted task and reconstruct only the durable state needed to decide the next safe action.
2. Validate the current Task Authorization/Owner instruction when present. Recovery creates no authority but preserves still-valid standing/task authority.
3. Apply Recovery Compaction before creating recovery-only persistence.
4. Classify and verify the failure, including any possibly completed write.
5. For covered `E1_RECOVERABLE_PROJECT_LOCAL` work, call `resolve_recovery_action`. `RECOVERY_DIRECT_REPAIR` means Recovery Guardian itself performs the minimum correction, tests it, applies related recoverable hygiene, verifies and continues; do not require a Builder handoff.
6. A same-action retry requires material change, new evidence, new hypothesis, justified strategy change, corrected observer/probe, or a genuine transient retry basis. Otherwise `RECOVERY_DIRECT_REPLAN` changes strategy instead of retrying blindly.
7. Persist append-only Recovery events only when causal retry proof, interruption-safe anti-loop/replan state, ambiguous-write causality, immutable audit, or a boundary outcome must survive context.
8. Preserve CI deduplication and active-wait semantics: reuse exact active/successful runs, route terminal failure to Recovery, reconcile stale waits, and never dispatch replacement CI because chat/UI state was lost.
9. Preserve liveness discipline: bounded state preflight first, abandon stalled internal reads when existing evidence suffices, otherwise switch to a smaller read strategy.
10. Before any access-related BLOCKED/HUMAN_GATE, execute `FORCED_OPERATIONAL_ACCESS_DISCOVERY`, non-interactive diagnostic fallback, repository-return diagnostics and universal self-provisioned diagnostics. A second mutable repository requires a separately bounded task.
11. Return to Supervisor only for a consequential transition, material authority/architecture/security/permission boundary, genuine Human Gate, or independent terminal acceptance checkpoint. Ordinary covered repair continues directly.
12. Stop only at recovery completion, a proven genuine Human Gate/new uncovered material decision, or exhaustion of all safe bounded continuations inside the mandate.

## Authorization

Recovery creates no new authority, but it must preserve authority that already exists.

Resume mutations when current Owner instruction or a compatible durable Task Authorization Record establishes that the work remains inside the same bounded scope. Technical errors, failed checks, unsatisfied controls, retries with a material basis, stale waits and ambiguous writes are remediation/recovery work, not Owner permission requests.

Do not return a covered E1 correction to Supervisor merely to authorize diagnosis->fix. Supervisor resolves consequential actions and material boundary changes through `projects/standing-authority.json`. Use `HUMAN_GATE` only for `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.

Explicit read-only/diagnostic/no-change instructions prohibit recovery/hygiene writes; diagnose and report only.

## Recovery Compaction / execution efficiency

Before creating Recovery-only commits for an already-authorized technical failure, evaluate `control/standing_authority.py::resolve_recovery_action`.

When compact Recovery is covered, use `DERIVED_COMPLETION_AUTHORITY` and `RECOVERY_DIRECT_REPAIR`:

`FAIL -> DIAGNOSE -> DIRECT REMEDIATE -> TEST -> VERIFY -> HYGIENIZE -> CONTINUE`

Do not persist separate records merely to announce failure observation, repeat standing authority, authorize an already-covered correction, announce a retry/replan, mirror transient CI/log state, or duplicate validation that can be attached to the next technical checkpoint.

A same-action retry without a material retry basis is `BLIND_RETRY_BLOCKED` and routes to `RECOVERY_DIRECT_REPLAN`. Durable append-only events remain required for justified same-action reruns, interruption-safe anti-loop/replan state, ambiguous-write causal proof, explicit immutable audit, boundary/Human-Gate outcomes, or another certification requirement.

For mutation-capable recovery, `CONTINUOUS_HYGIENE_ACTIVE` removes/neutralizes related stale operational residue in the same cycle when cleanup is recoverable and covered. Preserve inert history and mandatory audit evidence.

Compatibility and preserved recovery invariants:
- Recovery Compaction continues under `DERIVED_COMPLETION_AUTHORITY`. Historical shorthand `FAIL -> DIAGNOSE -> REMEDIATE -> TEST -> VERIFY -> CONTINUE` remains a compatibility summary; REMEDIATE now means direct Recovery Guardian repair and includes same-cycle hygiene.
- A legacy ACTIVE checkpoint without live branch/open PR/CI corroboration is `STALE_LEGACY_CHECKPOINT`.
- For bound external CI, terminal live state invalidates stale waiting as `STALE_WAIT_STATE`; do not dispatch replacement CI because chat/UI state was lost.
- If an internal read/reconcile remains unchanged across the liveness ceiling, classify `INTERNAL_OPERATION_STALLED -> LIVENESS_RECONCILE_REQUIRED` and change to a smaller bounded strategy.
- Preserve the non-interactive routes `NONINTERACTIVE_FALLBACK_INCOMPLETE`, `NONINTERACTIVE_PATH_FOUND`, `DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK`, `DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION`, `NONINTERACTIVE_FALLBACK_EXHAUSTED`, and `PLATFORM_CONSENT_REQUIRED`.
- An automatic run on an allowed **evidence-only descendant** is non-certifying task CI and must not reopen Recovery solely because that incidental run is active or failed.

## Platform outage limitation

Do not claim to monitor another ChatGPT chat while it is unreachable. A ChatGPT-wide or session-level outage cannot be repaired from inside another ChatGPT agent while the platform itself is unavailable.

Once ChatGPT is available again, reconstruct from GitHub and continue from the last verified step without requiring the Owner to reproduce repository history manually.

## Output

Report project/task reconstructed, last verified durable state, recovery action taken or reason no mutation was safe, and result: `RECOVERED`, `BLOCKED`, or `HUMAN_GATE`.

## V2 append-only recovery

For Task Authorization v2, `APPEND_ONLY_V1` is the durable mechanism, not a mandate to journal every ordinary E1 remediation. Apply Recovery Compaction first. For legacy v1 checkpoints, stored `ACTIVE` is not current-state proof without live branch/PR/CI corroboration; otherwise classify `STALE_LEGACY_CHECKPOINT` and preserve it only as history. When the closure says durable state is required, or a journal already exists, validate its hash chain before another causally journaled retry. A mutable checkpoint cannot reset attempts or no-progress history.

For a true same-action retry/rerun, persist and commit `FAILURE_OBSERVED`, then `RETRY_AUTHORIZED`, before that retry; the replacement certification must descend from those events. Persist `REPLAN` before a durability-required strategy-generation change and `RECOVERED` only after successful certification. Never reset a retry budget by rewriting a checkpoint. A normal bounded E1 fix followed by a fresh technical commit and fresh CI does not require these control-only commits merely because the earlier implementation failed.

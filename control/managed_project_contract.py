#!/usr/bin/env python3
import hashlib
import re
from datetime import datetime, timezone
from fnmatch import fnmatchcase

from control.validate_records import validate_checkpoint, validate_project_policy, validate_result, validate_scope, validate_task
from control.scope_policy import scope_pattern_is_within

NEW_TASK_SCHEMA_VERSION = "2.0"
WORKER_RESULT_SCHEMA_VERSION = "2.0"
RECOVERY_MODE = "APPEND_ONLY_V1"
CI_WAIT_STATE = "WAITING_EXTERNAL_CI"
CI_STALE_WAIT_STATE = "STALE_WAIT_STATE"
CI_ROUTE_WAIT = "WAIT"
CI_ROUTE_CONTINUE = "AUDIT_CONTINUE"
CI_ROUTE_RECOVERY = "RECOVERY"
CI_ROUTE_INVESTIGATE = "INVESTIGATE"
POLICY_BINDING_MODE = "CENTRAL_CONTROL_V1"
INTEGRITY_MODE = "IMMUTABLE_AUTHORIZATION_V1"
DEFAULT_POLL_INTERVAL_MINUTES = 5
DEFAULT_STALE_AFTER_MINUTES = 60
LEGACY_ACTIVE_CORROBORATED = "LEGACY_ACTIVE_CORROBORATED"
STALE_LEGACY_CHECKPOINT = "STALE_LEGACY_CHECKPOINT"
LEGACY_CHECKPOINT_TERMINAL = "LEGACY_CHECKPOINT_TERMINAL"
CI_DISPATCH_REQUIRED = "DISPATCH_REQUIRED"
CI_REUSE_ACTIVE = "REUSE_ACTIVE_RUN"
CI_REUSE_SUCCESS = "REUSE_SUCCESSFUL_RUN"
CI_DISPATCH_ROUTE_RECOVERY = "ROUTE_RECOVERY"
POST_CI_DESCENDANT_EVIDENCE_ONLY = "EVIDENCE_ONLY_DESCENDANT"
POST_CI_DESCENDANT_MATERIAL = "MATERIAL_DESCENDANT"
POST_CI_ROUTE_CERTIFICATION_UNCHANGED = "CERTIFICATION_UNCHANGED"
POST_CI_ROUTE_FINAL_HEAD_GOVERNANCE = "FINAL_HEAD_GOVERNANCE_CHECK"
POST_CI_ROUTE_FRESH_IMPLEMENTATION = "FRESH_IMPLEMENTATION_CI"


def validate_managed_task(task, repository, control_repository=None):
    validate_task(task)
    if task.get("schema_version") != NEW_TASK_SCHEMA_VERSION:
        raise ValueError("new managed-project mutation tasks must use Task Authorization v2")
    if task.get("repository") != repository:
        raise ValueError("managed task repository does not match active repository")
    if task.get("integrity_mode") != INTEGRITY_MODE:
        raise ValueError("new managed-project tasks must bind immutable authorization integrity")
    if (task.get("recovery") or {}).get("mode") != RECOVERY_MODE:
        raise ValueError("managed task recovery history must use APPEND_ONLY_V1")

    binding = task.get("policy") or {}
    if binding.get("binding_mode") != POLICY_BINDING_MODE:
        raise ValueError("managed-project tasks must use CENTRAL_CONTROL_V1 policy binding")
    if control_repository and binding.get("repository") != control_repository:
        raise ValueError("managed task policy repository does not match canonical control repository")

    required_ci = task.get("required_ci")
    if not isinstance(required_ci, list) or not all(isinstance(x, str) and x for x in required_ci):
        raise ValueError("managed task required_ci must be a list of non-empty workflow names")
    return True


def validate_managed_result(task, result, repository, control_repository=None):
    validate_managed_task(task, repository, control_repository)
    validate_result(result)
    if result.get("schema_version") != WORKER_RESULT_SCHEMA_VERSION:
        raise ValueError("managed-project Worker Result must use schema v2")
    if result.get("task_id") != task.get("task_id"):
        raise ValueError("managed task/result task_id mismatch")
    if result.get("repository") != repository:
        raise ValueError("managed result repository does not match active repository")
    if not result.get("authorization_commit_sha") or not result.get("authorization_sha256"):
        raise ValueError("managed Worker Result must bind the exact Task Authorization commit and digest")
    if result.get("terminal_status") == "TERMINAL_SUCCESS":
        by_name = {item.get("name"): item for item in result.get("ci", [])}
        for name in task["required_ci"]:
            item = by_name.get(name)
            if not item or item.get("status") != "SUCCESS" or not isinstance(item.get("run_id"), int):
                raise ValueError(f"managed terminal success requires live CI run_id evidence for {name}")
    return True


def policy_sha256(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def _task_transition_actions(task):
    items = task.get("transition_controls") or task.get("human_gates") or []
    return {item["action"] for item in items}


def _policy_transition_actions(effect_policy):
    return set(
        effect_policy.get("required_transition_controls")
        or effect_policy.get("required_human_gates")
        or []
    )


def verify_managed_task_against_control_policy(
    task,
    policy,
    policy_raw,
    actual_target_base_sha,
    changed_files,
    control_repository,
    control_revision,
    expected_policy_path,
):
    validate_managed_task(task, task["repository"], control_repository)
    validate_project_policy(policy)

    if policy.get("repository_mode") == "ACTIVE_TARGET":
        pass
    elif task["repository"] != policy.get("repository"):
        raise ValueError("task repository does not match central policy repository")
    if task["starting_state"]["base_sha"] != actual_target_base_sha:
        raise ValueError("task starting_state.base_sha does not match actual target PR base SHA")

    binding = task["policy"]
    if binding["repository"] != control_repository:
        raise ValueError("task policy repository does not match canonical control repository")
    if binding["revision"] != control_revision:
        raise ValueError("task policy revision does not match the exact control-plane revision")
    if binding["path"] != expected_policy_path:
        raise ValueError("task policy path does not match registered central policy path")
    if binding["profile"] != policy["policy_id"]:
        raise ValueError("task policy profile does not match central policy_id")
    if binding["sha256"] != policy_sha256(policy_raw):
        raise ValueError("task policy sha256 does not match exact central policy bytes")

    effect = task["effect_class"]
    effect_policy = policy["effect_policies"].get(effect)
    if not effect_policy:
        raise ValueError(f"central policy does not authorize effect class {effect}")

    protected = [
        path for path in changed_files
        if any(fnmatchcase(path, pattern) for pattern in policy["protected_paths"])
    ]
    if protected and effect != "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED":
        raise ValueError(
            "managed E1 task touches protected paths and requires a separate governance task: "
            + ", ".join(sorted(protected))
        )

    allowed_patterns = effect_policy["allowed_scope_patterns"]
    widened_patterns = sorted(
        pattern
        for pattern in task["mutation_scope"]
        if not any(scope_pattern_is_within(pattern, allowed) for allowed in allowed_patterns)
    )
    if widened_patterns:
        raise ValueError("managed task mutation_scope exceeds central policy ceiling: " + ", ".join(widened_patterns))

    allowed_actions = set(effect_policy["allowed_actions"])
    widened_actions = sorted(set(task["allowed_actions"]) - allowed_actions)
    if widened_actions:
        raise ValueError("managed task allowed_actions exceeds central policy ceiling: " + ", ".join(widened_actions))

    missing_prohibitions = sorted(
        set(effect_policy["required_prohibited_actions"]) - set(task["prohibited_actions"])
    )
    if missing_prohibitions:
        raise ValueError("managed task is missing required prohibitions: " + ", ".join(missing_prohibitions))

    task_gates = _task_transition_actions(task)
    missing_gates = sorted(_policy_transition_actions(effect_policy) - task_gates)
    if missing_gates:
        raise ValueError("managed task is missing required consequential transition controls: " + ", ".join(missing_gates))

    missing_ci = sorted(set(effect_policy["required_ci"]) - set(task["required_ci"]))
    if missing_ci:
        raise ValueError("managed task required_ci is weaker than central policy: " + ", ".join(missing_ci))
    allowed_ci = effect_policy.get("allowed_ci")
    if allowed_ci is not None:
        unknown_ci = sorted(set(task["required_ci"]) - set(allowed_ci))
        if unknown_ci:
            raise ValueError("managed task required_ci contains workflows outside central policy: " + ", ".join(unknown_ci))

    missing_validation = sorted(
        set(effect_policy["required_validation"]) - set(task["required_validation"])
    )
    if missing_validation:
        raise ValueError(
            "managed task required_validation is weaker than central policy: " + ", ".join(missing_validation)
        )

    validate_scope(task, changed_files)
    return True



def reconcile_legacy_checkpoint_liveness(
    checkpoint,
    has_live_branch=False,
    has_open_pr=False,
    has_active_ci=False,
    has_terminal_result=False,
):
    """Interpret legacy v1 checkpoint state against current durable evidence.

    Legacy checkpoint status is historical evidence. ACTIVE is actionable only
    when current repository state independently corroborates a live workstream.
    """
    validate_checkpoint(checkpoint)
    status = checkpoint.get("status")
    task_id = checkpoint.get("task_id")

    if status != "ACTIVE":
        return {
            "task_id": task_id,
            "state": LEGACY_CHECKPOINT_TERMINAL,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "legacy checkpoint already records a terminal/non-active state",
        }

    if has_terminal_result:
        return {
            "task_id": task_id,
            "state": STALE_LEGACY_CHECKPOINT,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "terminal task result supersedes legacy ACTIVE checkpoint snapshot",
        }

    live_evidence = bool(has_live_branch or has_open_pr or has_active_ci)
    if not live_evidence:
        return {
            "task_id": task_id,
            "state": STALE_LEGACY_CHECKPOINT,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "legacy ACTIVE checkpoint has no corroborating live branch, PR, or active CI",
        }

    return {
        "task_id": task_id,
        "state": LEGACY_ACTIVE_CORROBORATED,
        "actionable": True,
        "checkpoint_status": status,
        "reason": "legacy ACTIVE checkpoint is corroborated by current live workstream evidence",
    }



def decide_ci_dispatch(workflow_name, target_sha, event, workflow_runs):
    """Decide whether Project Leader should explicitly create another CI run.

    Deduplication is exact by workflow name, target SHA, and GitHub event
    context. Automatic runs from different contexts remain independent evidence.
    """
    for label, value in (
        ("workflow_name", workflow_name),
        ("target_sha", target_sha),
        ("event", event),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")
    if not isinstance(workflow_runs, list):
        raise ValueError("workflow_runs must be a list")

    matching = [
        run for run in workflow_runs
        if isinstance(run, dict)
        and run.get("name") == workflow_name
        and run.get("head_sha") == target_sha
        and run.get("event") == event
    ]
    if not matching:
        return {
            "decision": CI_DISPATCH_REQUIRED,
            "run_id": None,
            "reason": "no existing exact workflow/SHA/context run",
        }

    def order_key(run):
        timestamp = run.get("created_at") or run.get("run_started_at") or run.get("updated_at") or ""
        run_id = run.get("id")
        return (timestamp, run_id if isinstance(run_id, int) else -1)

    latest = max(matching, key=order_key)
    status = latest.get("status")
    conclusion = latest.get("conclusion")
    run_id = latest.get("id")

    if status in {"queued", "waiting", "pending", "requested", "in_progress"}:
        return {
            "decision": CI_REUSE_ACTIVE,
            "run_id": run_id,
            "reason": "exact matching CI run is already active",
        }
    if status == "completed" and conclusion == "success":
        return {
            "decision": CI_REUSE_SUCCESS,
            "run_id": run_id,
            "reason": "exact matching CI run already completed successfully",
        }
    if status == "completed":
        return {
            "decision": CI_DISPATCH_ROUTE_RECOVERY,
            "run_id": run_id,
            "reason": f"exact matching CI run is terminal non-success: {conclusion}",
        }
    return {
        "decision": "INVESTIGATE_CI_STATE",
        "run_id": run_id,
        "reason": f"unrecognized exact matching CI state: {status}",
    }


def _is_task_local_post_ci_evidence_path(path, task_id):
    if path == f".project-leader/results/{task_id}.json":
        return True
    if path.startswith(f".project-leader/recovery-events/{task_id}/") and path.endswith(".json"):
        return True
    if (
        path.startswith(f".project-leader/transitions/{task_id}-")
        and path.endswith(".result.json")
    ):
        return True
    return False


def classify_post_implementation_descendant(
    changed_files,
    task_id,
    final_head_checks_required=False,
):
    """Classify changes after a CI-certified implementation head.

    Required task CI is bound to implementation_head_sha. A newer PR head may
    contain only task-local Project Leader evidence metadata without becoming a
    new implementation head. Automatic CI that happens to run on such an
    evidence-only descendant is non-certifying and must not by itself reopen
    task Recovery. If repository governance explicitly requires checks on the
    current PR head, that CI is a merge-governance condition, not a reason to
    move implementation_head_sha or manufacture another evidence commit.
    """
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("task_id must be a non-empty string")
    if not isinstance(changed_files, list) or not all(
        isinstance(path, str) and path for path in changed_files
    ):
        raise ValueError("changed_files must be a list of non-empty paths")
    if not isinstance(final_head_checks_required, bool):
        raise ValueError("final_head_checks_required must be boolean")

    material = sorted(
        path
        for path in changed_files
        if not _is_task_local_post_ci_evidence_path(path, task_id)
    )
    if material:
        return {
            "state": POST_CI_DESCENDANT_MATERIAL,
            "route": POST_CI_ROUTE_FRESH_IMPLEMENTATION,
            "certification_ci_required": True,
            "final_head_checks_required": final_head_checks_required,
            "material_files": material,
        }

    return {
        "state": POST_CI_DESCENDANT_EVIDENCE_ONLY,
        "route": (
            POST_CI_ROUTE_FINAL_HEAD_GOVERNANCE
            if final_head_checks_required
            else POST_CI_ROUTE_CERTIFICATION_UNCHANGED
        ),
        "certification_ci_required": False,
        "final_head_checks_required": final_head_checks_required,
        "evidence_only_files": sorted(changed_files),
    }


def _parse_registry_projects(registry_text):
    projects = {}
    current = None
    in_projects = False
    for raw in registry_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw == "projects:":
            in_projects = True
            current = None
            continue
        if raw and not raw.startswith(" "):
            in_projects = False
            current = None
            continue
        if not in_projects:
            continue

        match_project = re.match(r"^  ([A-Za-z0-9._-]+):\s*$", raw)
        if match_project:
            current = match_project.group(1)
            projects[current] = {}
            continue
        if current is None:
            continue

        match_field = re.match(r'^    ([A-Za-z0-9_]+):\s*"?([^"]*)"?\s*$', raw)
        if match_field:
            projects[current][match_field.group(1)] = match_field.group(2)
    return projects


def validate_registry_profile_consistency(registry_text, profiles, policies):
    registry_projects = _parse_registry_projects(registry_text)
    profile_projects = profiles.get("profiles") or {}
    if set(registry_projects) != set(profile_projects):
        raise ValueError("registry and policy profile project sets differ")

    for project_id, entry in registry_projects.items():
        profile = profile_projects[project_id]
        if entry.get("repository") != profile.get("repository"):
            raise ValueError(f"{project_id}: registry/profile repository mismatch")
        if entry.get("default_branch") != profile.get("default_branch"):
            raise ValueError(f"{project_id}: registry/profile default_branch mismatch")
        policy_path = entry.get("policy")
        if not policy_path:
            raise ValueError(f"{project_id}: registry is missing executable central policy path")
        if profile.get("central_policy_path") != policy_path:
            raise ValueError(f"{project_id}: registry/profile central policy path mismatch")
        policy = policies.get(policy_path)
        if not policy:
            raise ValueError(f"{project_id}: central policy file is missing: {policy_path}")
        validate_project_policy(policy)
        if policy["repository"] != entry.get("repository"):
            raise ValueError(f"{project_id}: registry/policy repository mismatch")
        if policy["default_branch"] != entry.get("default_branch"):
            raise ValueError(f"{project_id}: registry/policy default_branch mismatch")
        allowed_ci = (policy.get("effect_policies") or {}).get("E1_RECOVERABLE_PROJECT_LOCAL", {}).get("allowed_ci", [])
        if set(profile.get("allowed_ci_names") or []) != set(allowed_ci):
            raise ValueError(f"{project_id}: profile/policy allowed CI mismatch")
    return True


def _parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_external_ci(run, now=None, stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES):
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status == "completed":
        return "COMPLETED_SUCCESS" if conclusion == "success" else "COMPLETED_FAILURE"
    if status not in {"queued", "in_progress", "waiting", "pending", "requested"}:
        return "INVESTIGATE_CI_STATE"

    now = now or datetime.now(timezone.utc)
    updated = (
        _parse_time(run.get("updated_at"))
        or _parse_time(run.get("run_started_at"))
        or _parse_time(run.get("created_at"))
    )
    if updated is not None:
        age_minutes = (now - updated).total_seconds() / 60
        if age_minutes > stale_after_minutes:
            return "INVESTIGATE_STALE_CI"
    return CI_WAIT_STATE


def reconcile_external_ci_wait(bound_run_ids, live_runs, previous_state=CI_WAIT_STATE, now=None, stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES):
    """Reconcile a persisted external-CI wait against fresh live GitHub run state.

    WAITING_EXTERNAL_CI is transient. Exact bound run IDs are re-read from GitHub;
    once every bound run is terminal, an older wait becomes STALE_WAIT_STATE and
    must route immediately to Supervisor audit/continue or Recovery.
    """
    if not isinstance(bound_run_ids, list) or not bound_run_ids:
        raise ValueError("external CI wait must bind at least one exact run_id")
    if len(set(bound_run_ids)) != len(bound_run_ids):
        raise ValueError("external CI wait run_ids must be unique")
    if not all(isinstance(run_id, int) and run_id > 0 for run_id in bound_run_ids):
        raise ValueError("external CI wait run_ids must be positive integers")
    if not isinstance(live_runs, list):
        raise ValueError("live_runs must be a list")

    by_id = {
        run.get("id"): run
        for run in live_runs
        if isinstance(run, dict) and isinstance(run.get("id"), int)
    }
    missing = [run_id for run_id in bound_run_ids if run_id not in by_id]
    if missing:
        return {
            "state": "INVESTIGATE_CI_STATE",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "missing_run_ids": missing,
        }

    classifications = {
        run_id: classify_external_ci(
            by_id[run_id],
            now=now,
            stale_after_minutes=stale_after_minutes,
        )
        for run_id in bound_run_ids
    }

    if any(value == "INVESTIGATE_STALE_CI" for value in classifications.values()):
        return {
            "state": "INVESTIGATE_STALE_CI",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "classifications": classifications,
        }
    if any(value == "INVESTIGATE_CI_STATE" for value in classifications.values()):
        return {
            "state": "INVESTIGATE_CI_STATE",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "classifications": classifications,
        }

    active = [run_id for run_id, value in classifications.items() if value == CI_WAIT_STATE]
    if active:
        return {
            "state": CI_WAIT_STATE,
            "route": CI_ROUTE_WAIT,
            "bound_run_ids": list(bound_run_ids),
            "active_run_ids": active,
            "classifications": classifications,
        }

    failed = [run_id for run_id, value in classifications.items() if value == "COMPLETED_FAILURE"]
    state = CI_STALE_WAIT_STATE if previous_state == CI_WAIT_STATE else (
        "COMPLETED_FAILURE" if failed else "COMPLETED_SUCCESS"
    )
    return {
        "state": state,
        "route": CI_ROUTE_RECOVERY if failed else CI_ROUTE_CONTINUE,
        "bound_run_ids": list(bound_run_ids),
        "failed_run_ids": failed,
        "classifications": classifications,
    }

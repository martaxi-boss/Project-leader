#!/usr/bin/env python3
from datetime import datetime, timezone

REQUIRED_CONTROL_CONTRACT = {
    "new_task_schema_version": "2.0",
    "worker_result_schema_version": "2.0",
    "recovery_mode": "APPEND_ONLY_V1",
    "ci_evidence_mode": "LIVE_GITHUB_RUN_ID_AND_SHA",
    "final_head_rule": "IMPLEMENTATION_ANCESTOR_OF_FINAL_HEAD",
    "trusted_gate_mode": "SUPERVISOR_EXTERNAL_AUDIT_REQUIRED_IF_PROJECT_LOCAL_GATE_ABSENT",
}


def validate_managed_profile(profile):
    contract = profile.get("control_contract")
    if not isinstance(contract, dict):
        raise ValueError("managed project profile is missing control_contract")
    for key, expected in REQUIRED_CONTROL_CONTRACT.items():
        if contract.get(key) != expected:
            raise ValueError(f"managed project control_contract.{key} must be {expected!r}")
    wait = contract.get("ci_wait")
    if not isinstance(wait, dict):
        raise ValueError("managed project control_contract.ci_wait is required")
    if wait.get("state") != "WAITING_EXTERNAL_CI":
        raise ValueError("managed project CI wait state must be WAITING_EXTERNAL_CI")
    if wait.get("retry_while_running") is not False:
        raise ValueError("managed project CI must not be retried while the current run is still running")
    if not isinstance(wait.get("poll_interval_minutes"), int) or wait["poll_interval_minutes"] < 1:
        raise ValueError("managed project CI poll_interval_minutes must be >= 1")
    if not isinstance(wait.get("stale_after_minutes"), int) or wait["stale_after_minutes"] < wait["poll_interval_minutes"]:
        raise ValueError("managed project CI stale_after_minutes must be >= poll_interval_minutes")
    allowed_ci = profile.get("allowed_ci_names")
    if not isinstance(allowed_ci, list) or not allowed_ci or not all(isinstance(x, str) and x for x in allowed_ci):
        raise ValueError("managed project profile requires non-empty allowed_ci_names")
    return True


def validate_managed_task(task, profile):
    validate_managed_profile(profile)
    if task.get("schema_version") != "2.0":
        raise ValueError("new managed-project mutation tasks must use Task Authorization v2")
    if task.get("repository") != profile.get("repository"):
        raise ValueError("managed task repository does not match registered profile")
    if (task.get("recovery") or {}).get("mode") != "APPEND_ONLY_V1":
        raise ValueError("managed task recovery history must use APPEND_ONLY_V1")
    required_ci = task.get("required_ci")
    if not isinstance(required_ci, list) or not required_ci:
        raise ValueError("managed task required_ci must be non-empty")
    unknown = sorted(set(required_ci) - set(profile["allowed_ci_names"]))
    if unknown:
        raise ValueError("managed task requires unregistered CI names: " + ", ".join(unknown))
    return True


def validate_managed_result(task, result, profile):
    validate_managed_task(task, profile)
    if result.get("schema_version") != "2.0":
        raise ValueError("managed-project Worker Result must use schema v2")
    if result.get("task_id") != task.get("task_id"):
        raise ValueError("managed task/result task_id mismatch")
    if result.get("repository") != profile.get("repository"):
        raise ValueError("managed result repository does not match registered profile")
    if result.get("terminal_status") == "TERMINAL_SUCCESS":
        by_name = {item.get("name"): item for item in result.get("ci", [])}
        for name in task["required_ci"]:
            item = by_name.get(name)
            if not item or item.get("status") != "SUCCESS" or not isinstance(item.get("run_id"), int):
                raise ValueError(f"managed terminal success requires live CI run_id evidence for {name}")
    return True


def _parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_external_ci(run, profile, now=None):
    validate_managed_profile(profile)
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status == "completed":
        return "COMPLETED_SUCCESS" if conclusion == "success" else "COMPLETED_FAILURE"
    if status not in {"queued", "in_progress", "waiting", "pending", "requested"}:
        return "INVESTIGATE_CI_STATE"

    now = now or datetime.now(timezone.utc)
    updated = _parse_time(run.get("updated_at")) or _parse_time(run.get("run_started_at")) or _parse_time(run.get("created_at"))
    if updated is not None:
        age_minutes = (now - updated).total_seconds() / 60
        stale_after = profile["control_contract"]["ci_wait"]["stale_after_minutes"]
        if age_minutes > stale_after:
            return "INVESTIGATE_STALE_CI"
    return "WAITING_EXTERNAL_CI"

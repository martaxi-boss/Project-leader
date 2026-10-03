#!/usr/bin/env python3
from datetime import datetime, timezone

NEW_TASK_SCHEMA_VERSION = "2.0"
WORKER_RESULT_SCHEMA_VERSION = "2.0"
RECOVERY_MODE = "APPEND_ONLY_V1"
CI_WAIT_STATE = "WAITING_EXTERNAL_CI"
DEFAULT_POLL_INTERVAL_MINUTES = 5
DEFAULT_STALE_AFTER_MINUTES = 60


def validate_managed_task(task, repository):
    if task.get("schema_version") != NEW_TASK_SCHEMA_VERSION:
        raise ValueError("new managed-project mutation tasks must use Task Authorization v2")
    if task.get("repository") != repository:
        raise ValueError("managed task repository does not match active repository")
    if (task.get("recovery") or {}).get("mode") != RECOVERY_MODE:
        raise ValueError("managed task recovery history must use APPEND_ONLY_V1")
    required_ci = task.get("required_ci")
    if not isinstance(required_ci, list) or not required_ci or not all(isinstance(x, str) and x for x in required_ci):
        raise ValueError("managed task required_ci must be non-empty")
    return True


def validate_managed_result(task, result, repository):
    validate_managed_task(task, repository)
    if result.get("schema_version") != WORKER_RESULT_SCHEMA_VERSION:
        raise ValueError("managed-project Worker Result must use schema v2")
    if result.get("task_id") != task.get("task_id"):
        raise ValueError("managed task/result task_id mismatch")
    if result.get("repository") != repository:
        raise ValueError("managed result repository does not match active repository")
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


def classify_external_ci(
    run,
    now=None,
    stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES,
):
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
        if age_minutes > stale_after_minutes:
            return "INVESTIGATE_STALE_CI"
    return CI_WAIT_STATE

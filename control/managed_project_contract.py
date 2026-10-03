#!/usr/bin/env python3
import hashlib
import re
from datetime import datetime, timezone
from fnmatch import fnmatchcase

from control.validate_records import validate_project_policy, validate_result, validate_scope, validate_task
from control.scope_policy import scope_pattern_is_within

NEW_TASK_SCHEMA_VERSION = "2.0"
WORKER_RESULT_SCHEMA_VERSION = "2.0"
RECOVERY_MODE = "APPEND_ONLY_V1"
CI_WAIT_STATE = "WAITING_EXTERNAL_CI"
POLICY_BINDING_MODE = "CENTRAL_CONTROL_V1"
INTEGRITY_MODE = "IMMUTABLE_AUTHORIZATION_V1"
DEFAULT_POLL_INTERVAL_MINUTES = 5
DEFAULT_STALE_AFTER_MINUTES = 60


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
    if not isinstance(required_ci, list) or not required_ci or not all(isinstance(x, str) and x for x in required_ci):
        raise ValueError("managed task required_ci must be non-empty")
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

    if task["repository"] != policy["repository"]:
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

    task_gates = {
        item["action"] for item in task["human_gates"] if item["requires_owner_approval"] is True
    }
    missing_gates = sorted(set(effect_policy["required_human_gates"]) - task_gates)
    if missing_gates:
        raise ValueError("managed task is missing required Human Gates: " + ", ".join(missing_gates))

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

#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control.scope_policy import scope_pattern_is_within
from control.validate_records import (
    validate_pair,
    validate_project_policy,
    validate_scope,
    validate_task,
)

TRANSITION_AUTHORIZATION_PATTERN = ".project-leader/transitions/*.authorization.json"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def policy_sha256(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def canonical_task_path(task):
    return f".project-leader/tasks/{task['task_id']}.json"


def expand_changed_files(changes):
    """Return exact Git path identities, preserving rename/copy origins."""
    expanded = []
    for item in changes:
        if isinstance(item, str):
            paths = [item]
        elif isinstance(item, dict):
            paths = [item.get("filename")]
            previous = item.get("previous_filename")
            if previous is not None:
                paths.append(previous)
        else:
            raise ValueError("changed-file entry must be a path string or object")

        for path in paths:
            if not isinstance(path, str) or not path:
                raise ValueError("changed-file entry is missing an exact path")
            if path not in expanded:
                expanded.append(path)
    return expanded


def _task_transition_actions(task):
    items = task.get("transition_controls") or task.get("human_gates") or []
    return {item["action"] for item in items}


def _policy_transition_actions(effect_policy):
    return set(
        effect_policy.get("required_transition_controls")
        or effect_policy.get("required_human_gates")
        or []
    )


def verify_pr_evidence_context(
    *,
    declared_changed_count,
    observed_changes,
    event_base_sha,
    live_base_sha,
    api_limit=3000,
):
    if not isinstance(declared_changed_count, int) or isinstance(declared_changed_count, bool):
        raise ValueError("declared_changed_count must be an integer")
    if declared_changed_count < 0:
        raise ValueError("declared_changed_count must be non-negative")
    if declared_changed_count >= api_limit:
        raise ValueError(
            f"PR changed-file evidence reached GitHub's {api_limit}-file limit and is not certifiable"
        )
    if declared_changed_count != len(observed_changes):
        raise ValueError(
            "PR changed-file evidence is incomplete: "
            f"declared={declared_changed_count} observed={len(observed_changes)}"
        )
    if event_base_sha != live_base_sha:
        raise ValueError(
            f"trusted gate base is stale: event={event_base_sha} live={live_base_sha}"
        )
    return True


def verify_promotable_result(task, result):
    validate_pair(task, result)
    if result.get("terminal_status") != "TERMINAL_SUCCESS":
        raise ValueError(
            "trusted authorization gate certifies promotion only for TERMINAL_SUCCESS"
        )
    return True


def verify_task_against_base_policy(
    task,
    policy,
    policy_raw,
    actual_base_sha,
    changed_files,
    expected_policy_path,
    actual_task_path=None,
):
    validate_task(task)
    validate_project_policy(policy)

    if task["schema_version"] != "2.0":
        raise ValueError("trusted gate requires Task Authorization schema_version 2.0")
    if task.get("integrity_mode") != "IMMUTABLE_AUTHORIZATION_V1":
        raise ValueError("trusted gate requires immutable v2 Task Authorization")

    expected_task_path = canonical_task_path(task)
    if actual_task_path is not None and actual_task_path != expected_task_path:
        raise ValueError(
            f"Task Authorization path must be canonical: {expected_task_path}"
        )

    if task["repository"] != policy["repository"]:
        raise ValueError("task repository does not match base policy repository")

    if task["starting_state"]["base_sha"] != actual_base_sha:
        raise ValueError("task starting_state.base_sha does not match actual PR base SHA")

    binding = task["policy"]
    if binding["base_sha"] != actual_base_sha:
        raise ValueError("task policy.base_sha does not match actual PR base SHA")
    if binding["path"] != expected_policy_path:
        raise ValueError("task policy.path does not match trusted workflow policy path")
    if binding["profile"] != policy["policy_id"]:
        raise ValueError("task policy.profile does not match base policy_id")

    actual_digest = policy_sha256(policy_raw)
    if binding["sha256"] != actual_digest:
        raise ValueError("task policy.sha256 does not match the exact base policy bytes")

    effect = task["effect_class"]
    effect_policy = policy["effect_policies"].get(effect)
    if not effect_policy:
        raise ValueError(f"base policy does not authorize effect class {effect}")

    exact_changed_files = expand_changed_files(changed_files)
    protected_patterns = list(policy["protected_paths"]) + [
        TRANSITION_AUTHORIZATION_PATTERN
    ]
    protected = [
        path
        for path in exact_changed_files
        if any(fnmatchcase(path, pattern) for pattern in protected_patterns)
    ]
    if protected and effect != "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED":
        raise ValueError(
            "trusted gate forbids trust-root mutation outside an explicit E3 governance task: "
            + ", ".join(sorted(protected))
        )

    allowed_patterns = effect_policy["allowed_scope_patterns"]
    widened_patterns = sorted(
        pattern
        for pattern in task["mutation_scope"]
        if not any(scope_pattern_is_within(pattern, allowed) for allowed in allowed_patterns)
    )
    if widened_patterns:
        raise ValueError(
            "task mutation_scope exceeds base policy ceiling: "
            + ", ".join(widened_patterns)
        )

    allowed_actions = set(effect_policy["allowed_actions"])
    widened_actions = sorted(set(task["allowed_actions"]) - allowed_actions)
    if widened_actions:
        raise ValueError(
            "task allowed_actions exceeds base policy ceiling: "
            + ", ".join(widened_actions)
        )

    missing_prohibitions = sorted(
        set(effect_policy["required_prohibited_actions"])
        - set(task["prohibited_actions"])
    )
    if missing_prohibitions:
        raise ValueError(
            "task is missing required prohibitions: "
            + ", ".join(missing_prohibitions)
        )

    task_gates = _task_transition_actions(task)
    missing_gates = sorted(_policy_transition_actions(effect_policy) - task_gates)
    if missing_gates:
        raise ValueError(
            "task is missing required consequential transition controls: "
            + ", ".join(missing_gates)
        )

    missing_ci = sorted(set(effect_policy["required_ci"]) - set(task["required_ci"]))
    if missing_ci:
        raise ValueError(
            "task required_ci is weaker than base policy: " + ", ".join(missing_ci)
        )
    allowed_ci = effect_policy.get("allowed_ci")
    if allowed_ci is not None:
        unknown_ci = sorted(set(task["required_ci"]) - set(allowed_ci))
        if unknown_ci:
            raise ValueError(
                "task required_ci contains workflows outside base policy: "
                + ", ".join(unknown_ci)
            )

    missing_validation = sorted(
        set(effect_policy["required_validation"])
        - set(task["required_validation"])
    )
    if missing_validation:
        raise ValueError(
            "task required_validation is weaker than base policy: "
            + ", ".join(missing_validation)
        )

    validate_scope(task, exact_changed_files)
    return True


def _load_changed_file(path):
    raw = Path(path).read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [line for line in raw.splitlines() if line != ""]
    if not isinstance(parsed, list):
        raise ValueError("changed-file payload must be a JSON array")
    return parsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--live-base-sha", required=True)
    parser.add_argument("--declared-changed-count", required=True, type=int)
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--expected-policy-path", required=True)
    args = parser.parse_args()

    task = _read_json(args.task)
    result = _read_json(args.result)
    policy_path = Path(args.policy)
    policy_raw = policy_path.read_bytes()
    policy = json.loads(policy_raw.decode("utf-8"))
    changed_files = _load_changed_file(args.changed_files)
    verify_pr_evidence_context(
        declared_changed_count=args.declared_changed_count,
        observed_changes=changed_files,
        event_base_sha=args.base_sha,
        live_base_sha=args.live_base_sha,
    )

    verify_task_against_base_policy(
        task,
        policy,
        policy_raw,
        args.base_sha,
        changed_files,
        args.expected_policy_path,
        actual_task_path=args.task_path,
    )
    verify_promotable_result(task, result)
    print("TRUSTED_GATE_VALID")


if __name__ == "__main__":
    main()

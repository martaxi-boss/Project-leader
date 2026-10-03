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

from control.validate_records import validate_project_policy, validate_scope, validate_task


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def policy_sha256(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def verify_task_against_base_policy(task, policy, policy_raw, actual_base_sha, changed_files, expected_policy_path):
    validate_task(task)
    validate_project_policy(policy)

    if task["schema_version"] != "2.0":
        raise ValueError("trusted gate requires Task Authorization schema_version 2.0")

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

    protected = [
        path for path in changed_files
        if any(fnmatchcase(path, pattern) for pattern in policy["protected_paths"])
    ]
    if protected and effect != "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED":
        raise ValueError(
            "trusted gate forbids trust-root mutation outside an explicit E3 governance task: "
            + ", ".join(sorted(protected))
        )

    allowed_patterns = set(effect_policy["allowed_scope_patterns"])
    widened_patterns = sorted(set(task["mutation_scope"]) - allowed_patterns)
    if widened_patterns:
        raise ValueError("task mutation_scope exceeds base policy ceiling: " + ", ".join(widened_patterns))

    allowed_actions = set(effect_policy["allowed_actions"])
    widened_actions = sorted(set(task["allowed_actions"]) - allowed_actions)
    if widened_actions:
        raise ValueError("task allowed_actions exceeds base policy ceiling: " + ", ".join(widened_actions))

    missing_prohibitions = sorted(set(effect_policy["required_prohibited_actions"]) - set(task["prohibited_actions"]))
    if missing_prohibitions:
        raise ValueError("task is missing required prohibitions: " + ", ".join(missing_prohibitions))

    task_gates = {item["action"] for item in task["human_gates"] if item["requires_owner_approval"] is True}
    missing_gates = sorted(set(effect_policy["required_human_gates"]) - task_gates)
    if missing_gates:
        raise ValueError("task is missing required Human Gates: " + ", ".join(missing_gates))

    missing_ci = sorted(set(effect_policy["required_ci"]) - set(task["required_ci"]))
    if missing_ci:
        raise ValueError("task required_ci is weaker than base policy: " + ", ".join(missing_ci))

    missing_validation = sorted(set(effect_policy["required_validation"]) - set(task["required_validation"]))
    if missing_validation:
        raise ValueError("task required_validation is weaker than base policy: " + ", ".join(missing_validation))

    validate_scope(task, changed_files)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--expected-policy-path", required=True)
    args = parser.parse_args()

    task = _read_json(args.task)
    policy_path = Path(args.policy)
    policy_raw = policy_path.read_bytes()
    policy = json.loads(policy_raw.decode("utf-8"))
    changed_files = [
        line.strip()
        for line in Path(args.changed_files).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    verify_task_against_base_policy(
        task,
        policy,
        policy_raw,
        args.base_sha,
        changed_files,
        args.expected_policy_path,
    )
    print("TRUSTED_GATE_VALID")


if __name__ == "__main__":
    main()

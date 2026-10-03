import unittest
from datetime import datetime, timezone

from control.managed_project_contract import (
    classify_external_ci,
    validate_managed_result,
    validate_managed_task,
)

REPOSITORY = "owner/project"
CONTROL_REPOSITORY = "owner/control"


def task(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "project": "TEST",
        "repository": REPOSITORY,
        "created_at": "2026-10-03T01:00:00Z",
        "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "bounded managed task",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/task-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["src/**", ".project-leader/tasks/**", ".project-leader/results/**"],
        "allowed_actions": ["create_branch", "edit_project_files", "create_commits", "run_ci", "open_or_update_pull_request"],
        "prohibited_actions": ["merge_to_main"],
        "human_gates": [{"action": "merge_to_main", "requires_owner_approval": True}],
        "required_validation": ["Mutation scope audit", "GitHub evidence verification"],
        "required_ci": ["Project CI"],
        "policy": {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "repository": CONTROL_REPOSITORY,
            "revision": "c" * 40,
            "sha256": "d" * 64,
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "green PR",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }


def result(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "repository": REPOSITORY,
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "authorization_record": ".project-leader/tasks/TASK-001.json",
        "authorization_commit_sha": "b" * 40,
        "authorization_sha256": "e" * 64,
        "implementation_head_sha": "f" * 40,
        "branch": "builder/task-001",
        "terminal_status": "TERMINAL_SUCCESS",
        "changes": ["src/app.py"],
        "validation": [{"name": "Mutation scope audit", "status": "PASS", "evidence": "diff checked"}],
        "ci": [{"name": "Project CI", "status": "SUCCESS", "run_id": 123}],
        "material_non_effects": ["no merge"],
        "residual_blockers": [],
    }


class ManagedProjectContractTests(unittest.TestCase):
    def test_new_managed_task_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_task(task("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_central_policy_binding(self):
        item = task()
        item["policy"] = {
            "binding_mode": "LOCAL_BASE_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "base_sha": "a" * 40,
            "sha256": "d" * 64,
        }
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_immutable_authorization(self):
        item = task()
        del item["integrity_mode"]
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_append_only_recovery(self):
        item = task()
        item["recovery"]["mode"] = "MUTABLE_CHECKPOINT"
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_ci(self):
        item = task()
        item["required_ci"] = []
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_result(task(), result("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_requires_authorization_binding(self):
        item = result()
        del item["authorization_sha256"]
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_terminal_success_requires_real_run_id(self):
        item = result()
        item["ci"][0]["run_id"] = None
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_recent_in_progress_ci_is_wait_not_failure(self):
        run = {"status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:25:12Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "WAITING_EXTERNAL_CI")

    def test_old_in_progress_ci_requires_investigation_not_retry(self):
        run = {"status": "in_progress", "conclusion": None, "updated_at": "2026-10-02T22:00:00Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "INVESTIGATE_STALE_CI")

    def test_completed_success_is_terminal_success(self):
        self.assertEqual(classify_external_ci({"status": "completed", "conclusion": "success"}), "COMPLETED_SUCCESS")


if __name__ == "__main__":
    unittest.main()

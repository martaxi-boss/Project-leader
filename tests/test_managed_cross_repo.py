import hashlib
import json
import unittest
from pathlib import Path

from control.managed_project_contract import (
    validate_registry_profile_consistency,
    verify_managed_task_against_control_policy,
)
ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "owner/project"
CONTROL_REPOSITORY = "owner/control"


def task():
    return {
        "schema_version": "2.0",
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
        "human_gates": [{"action": "merge_to_main", "requires_authority_resolution": True}],
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




def policy():
    return {
        "schema_version": "1.0",
        "policy_id": "project-v1",
        "project": "TEST",
        "repository": REPOSITORY,
        "default_branch": "main",
        "effect_policies": {
            "E1_RECOVERABLE_PROJECT_LOCAL": {
                "allowed_scope_patterns": ["src/**", ".project-leader/tasks/**", ".project-leader/results/**"],
                "allowed_actions": ["create_branch", "edit_project_files", "create_commits", "run_ci", "open_or_update_pull_request"],
                "required_prohibited_actions": ["merge_to_main"],
                "required_human_gates": ["merge_to_main"],
                "required_ci": [],
                "allowed_ci": ["Project CI"],
                "required_validation": ["Mutation scope audit", "GitHub evidence verification"],
            }
        },
        "sensitive_paths": ["src/**"],
        "protected_paths": [".github/workflows/**"],
    }


class ManagedCrossRepositoryTests(unittest.TestCase):
    def make(self):
        p = policy()
        raw = (json.dumps(p, indent=2) + "\n").encode("utf-8")
        t = task()
        t["policy"]["sha256"] = hashlib.sha256(raw).hexdigest()
        return t, p, raw

    def test_target_base_and_control_revision_are_independent(self):
        t, p, raw = self.make()
        self.assertNotEqual(t["starting_state"]["base_sha"], t["policy"]["revision"])
        self.assertTrue(
            verify_managed_task_against_control_policy(
                t,
                p,
                raw,
                "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY,
                "c" * 40,
                "projects/policies/project.json",
            )
        )

    def test_wrong_control_revision_fails(self):
        t, p, raw = self.make()
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "9" * 40, "projects/policies/project.json"
            )

    def test_policy_bytes_are_exactly_bound(self):
        t, p, raw = self.make()
        t["policy"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_protected_target_path_requires_governance_task(self):
        t, p, raw = self.make()
        t["mutation_scope"].append(".github/workflows/**")
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".github/workflows/ci.yml"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_unregistered_ci_name_fails(self):
        t, p, raw = self.make()
        t["required_ci"] = ["Other CI"]
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_exact_file_scope_can_narrow_managed_policy_pattern(self):
        t, p, raw = self.make()
        t["mutation_scope"] = ["src/app.py", ".project-leader/tasks/TASK-001.json"]
        self.assertTrue(
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )
        )

    def test_nested_subpattern_can_narrow_managed_policy_pattern(self):
        t, p, raw = self.make()
        t["mutation_scope"] = ["src/feature/**", ".project-leader/tasks/**"]
        self.assertTrue(
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/feature/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )
        )

    def test_managed_scope_prefix_collision_fails_closed(self):
        t, p, raw = self.make()
        t["mutation_scope"] = ["src-escape/**", ".project-leader/tasks/**"]
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src-escape/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_managed_parent_traversal_scope_fails_closed(self):
        t, p, raw = self.make()
        t["mutation_scope"] = ["src/../secrets/**", ".project-leader/tasks/**"]
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_development_merge_action_is_explicitly_policy_bounded(self):
        t, p, _ = self.make()
        t["allowed_actions"].append("merge_development_branch")
        p["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]["allowed_actions"].append(
            "merge_development_branch"
        )
        raw = (json.dumps(p, indent=2) + "\n").encode("utf-8")
        t["policy"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.assertTrue(
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )
        )

    def test_merge_to_main_remains_outside_allowed_actions(self):
        t, p, raw = self.make()
        t["allowed_actions"].append("merge_to_main")
        with self.assertRaises(ValueError):
            verify_managed_task_against_control_policy(
                t, p, raw, "a" * 40,
                ["src/app.py", ".project-leader/tasks/TASK-001.json"],
                CONTROL_REPOSITORY, "c" * 40, "projects/policies/project.json"
            )

    def test_real_managed_policies_separate_development_merge_from_main_gate(self):
        for path in (
            "projects/policies/pink-iptv.json",
            "projects/policies/fadego.json",
            "projects/policies/vcam-pro.json",
        ):
            policy_data = json.loads((ROOT / path).read_text(encoding="utf-8"))
            e1 = policy_data["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]
            self.assertIn("merge_development_branch", e1["allowed_actions"], path)
            self.assertNotIn("merge_to_main", e1["allowed_actions"], path)
            self.assertIn("merge_to_main", e1["required_prohibited_actions"], path)
            self.assertIn("merge_to_main", e1["required_human_gates"], path)

    def test_real_registry_profiles_and_policies_are_consistent(self):
        registry = (ROOT / "projects/registry.yaml").read_text(encoding="utf-8")
        profiles = json.loads((ROOT / "projects/policy-profiles.json").read_text(encoding="utf-8"))
        policies = {}
        for path in (
            "projects/policies/pink-iptv.json",
            "projects/policies/fadego.json",
            "projects/policies/vcam-pro.json",
        ):
            policies[path] = json.loads((ROOT / path).read_text(encoding="utf-8"))
        self.assertTrue(validate_registry_profile_consistency(registry, profiles, policies))


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import unittest
from pathlib import Path

from control.trusted_gate import verify_task_against_base_policy

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "projects/policies/project-leader.json"


def make_task(policy_raw):
    base = "a" * 40
    return {
        "schema_version": "2.0",
        "task_id": "TEST-TRUSTED-001",
        "project": "PROJECT LEADER",
        "repository": "martaxi-boss/Project-leader",
        "created_at": "2026-10-02T22:30:00Z",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "bounded test",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {"default_branch": "main", "base_sha": base, "task_branch": "builder/test", "pr_number": None},
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["control/**", ".project-leader/tasks/**"],
        "allowed_actions": ["create_branch", "edit_project_files", "create_commits", "run_ci", "open_or_update_pull_request"],
        "prohibited_actions": [
            "merge_to_main", "branch_protection_or_ruleset_change", "release_or_publish",
            "license_selection", "managed_project_mutation", "production_deploy",
            "production_secret_change", "paid_service_activation",
        ],
        "human_gates": [
            {"action": "merge_to_main", "requires_owner_approval": True},
            {"action": "branch_protection_or_ruleset_change", "requires_owner_approval": True},
            {"action": "release_or_publish", "requires_owner_approval": True},
            {"action": "license_selection", "requires_owner_approval": True},
            {"action": "managed_project_mutation", "requires_owner_approval": True},
        ],
        "required_validation": ["Mutation scope audit", "GitHub evidence verification"],
        "required_ci": ["Control contract tests", "Validate control plane", "Package ChatGPT plugins"],
        "policy": {
            "profile": "project-leader-v1",
            "path": "projects/policies/project-leader.json",
            "base_sha": base,
            "sha256": hashlib.sha256(policy_raw).hexdigest(),
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "green",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }


class TrustedGateTests(unittest.TestCase):
    def setUp(self):
        self.raw = POLICY_PATH.read_bytes()
        self.policy = json.loads(self.raw)
        self.task = make_task(self.raw)
        self.changed = ["control/trusted_gate.py", ".project-leader/tasks/TEST-TRUSTED-001.json"]

    def verify(self, task=None):
        return verify_task_against_base_policy(
            task or self.task,
            self.policy,
            self.raw,
            "a" * 40,
            self.changed,
            "projects/policies/project-leader.json",
        )

    def test_valid_task_passes_base_policy(self):
        self.assertTrue(self.verify())

    def test_scope_cannot_self_widen_to_double_star(self):
        self.task["mutation_scope"] = ["**"]
        with self.assertRaises(ValueError):
            self.verify()

    def test_action_cannot_self_widen(self):
        self.task["allowed_actions"].append("merge_to_main")
        with self.assertRaises(ValueError):
            self.verify()

    def test_policy_digest_is_exact_base_bytes(self):
        self.task["policy"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.verify()

    def test_claimed_base_must_equal_real_pr_base(self):
        self.task["starting_state"]["base_sha"] = "b" * 40
        self.task["policy"]["base_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            self.verify()

    def test_required_ci_cannot_be_omitted(self):
        self.task["required_ci"].remove("Package ChatGPT plugins")
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == "__main__":
    unittest.main()

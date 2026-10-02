import json
import tempfile
import unittest
from pathlib import Path

from control.validate_records import validate_result, validate_task

ROOT = Path(__file__).resolve().parents[1]

class ControlContractTests(unittest.TestCase):
    def test_schemas_are_valid_json_and_require_core_fields(self):
        task = json.loads((ROOT / "control/task-authorization.schema.json").read_text())
        result = json.loads((ROOT / "control/worker-result.schema.json").read_text())
        self.assertIn("task_id", task["required"])
        self.assertIn("human_gates", task["required"])
        self.assertIn("implementation_head_sha", result["required"])
        self.assertIn("material_non_effects", result["required"])

    def test_plugins_use_same_required_github_connector(self):
        pl = json.loads((ROOT / "plugins/project-leader/.app.json").read_text())
        rg = json.loads((ROOT / "plugins/recovery-guardian/.app.json").read_text())
        self.assertTrue(pl["apps"]["github"]["required"])
        self.assertEqual(pl["apps"]["github"]["id"], rg["apps"]["github"]["id"])

    def test_current_task_authorization_record_validates(self):
        record = json.loads((ROOT / ".project-leader/tasks/PROJECT-LEADER-CONTROL-HARDENING-003.json").read_text())
        self.assertTrue(validate_task(record))
        self.assertFalse(record["privacy"]["contains_secrets"])
        self.assertFalse(record["privacy"]["contains_private_conversation_text"])

    def test_worker_result_validator_accepts_minimal_success(self):
        sample = {
            "schema_version": "1.0",
            "task_id": "TEST-WORKER-001",
            "terminal_status": "TERMINAL_SUCCESS",
            "repository": "owner/repo",
            "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
            "authorization_record": ".project-leader/tasks/TEST-WORKER-001.json",
            "implementation_head_sha": "a" * 40,
            "branch": "builder/test-worker-001",
            "pr_number": 1,
            "changes": ["example"],
            "validation": [{"name": "unit", "status": "PASS", "evidence": "local"}],
            "ci": [],
            "artifacts": [],
            "material_non_effects": ["no merge"],
            "residual_blockers": [],
        }
        self.assertTrue(validate_result(sample))

    def test_contracts_reference_durable_authorization(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text()
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text()
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text()
        self.assertIn(".project-leader/tasks/<task-id>.json", project)
        self.assertIn("Task Authorization Record", skill)
        self.assertIn("GitHub history without a compatible task authorization record", recovery)

if __name__ == "__main__":
    unittest.main()

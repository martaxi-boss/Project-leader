import json
import unittest
from pathlib import Path

from control.managed_project_contract import (
    CONTROL_MODE_DURABLE,
    CONTROL_MODE_FAST_E1,
    DIAGNOSIS_BUYS_DECISION,
    PROBE_NO_DECISION_VALUE,
    REGRESSION_FIRST,
    SAFE_ROLLBACK,
    evaluate_diagnostic_probe,
    resolve_control_mode,
    resolve_regression_strategy,
)
from control.trusted_gate import verify_fast_path_against_base_policy

ROOT = Path(__file__).resolve().parents[1]


class ExecutionFirstContractTests(unittest.TestCase):
    def test_normal_e1_uses_fast_path_without_durable_records(self):
        decision = resolve_control_mode("E1_RECOVERABLE_PROJECT_LOCAL")
        self.assertEqual(CONTROL_MODE_FAST_E1, decision["mode"])
        self.assertFalse(decision["durable_records_required"])
        self.assertIn("EXECUTE", decision["route"])

    def test_material_boundary_keeps_durable_control(self):
        for kwargs in (
            {"architecture_change": True},
            {"destructive": True},
            {"permission_change": True},
            {"irreversible": True},
            {"ambiguous_write_replay_risk": True},
        ):
            with self.subTest(kwargs=kwargs):
                decision = resolve_control_mode("E1_RECOVERABLE_PROJECT_LOCAL", **kwargs)
                self.assertEqual(CONTROL_MODE_DURABLE, decision["mode"])
                self.assertTrue(decision["durable_records_required"])

    def test_diagnosis_must_buy_a_decision(self):
        useless = evaluate_diagnostic_probe(
            "Which hypothesis is true?",
            ["A", "B"],
            {"A": "apply same fix", "B": "apply same fix"},
        )
        self.assertFalse(useless["execute_probe"])
        self.assertEqual(PROBE_NO_DECISION_VALUE, useless["reason"])

        useful = evaluate_diagnostic_probe(
            "Which subsystem regressed?",
            ["A", "B"],
            {"A": "revert A", "B": "repair B"},
        )
        self.assertTrue(useful["execute_probe"])
        self.assertEqual(DIAGNOSIS_BUYS_DECISION, useful["reason"])

    def test_regression_first_and_safe_rollback(self):
        first = resolve_regression_strategy(
            last_known_good="good",
            first_known_bad="bad",
            recent_change=True,
        )
        self.assertEqual(REGRESSION_FIRST, first["decision"])
        self.assertEqual(["good", "bad"], first["compare"])

        rollback = resolve_regression_strategy(
            last_known_good="good",
            first_known_bad="bad",
            recent_change=True,
            regression_confirmed=True,
        )
        self.assertEqual(SAFE_ROLLBACK, rollback["decision"])

    def test_fast_gate_accepts_e1_and_rejects_material_or_control_only_paths(self):
        policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            verify_fast_path_against_base_policy(
                policy, [{"filename": "tests/example_regression.py"}]
            )
        )
        with self.assertRaisesRegex(ValueError, "material/protected"):
            verify_fast_path_against_base_policy(
                policy, [{"filename": "control/managed_project_contract.py"}]
            )
        with self.assertRaisesRegex(ValueError, "control-only"):
            verify_fast_path_against_base_policy(
                policy,
                [{"filename": ".project-leader/tasks/SHOULD-NOT-EXIST.json"}],
            )

    def test_stale_base_workflow_invalidates_previous_green_head(self):
        workflow = (ROOT / ".github/workflows/trusted-pr-gate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("push:", workflow)
        self.assertIn("checks: write", workflow)
        self.assertIn("Base advanced; recertification required", workflow)
        self.assertIn("live_base_sha", workflow)
        self.assertIn("trusted-authorization", workflow)

    def test_skill_is_execution_first_and_progressively_loaded(self):
        skill = (
            ROOT / "plugins/project-leader/skills/project-leader/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("EXECUTION_FIRST_WITHIN_BOUNDS", skill)
        self.assertIn("PROGRESS_OVER_PROCESS", skill)
        self.assertIn("FUNCTIONAL_CONVERGENCE_FIRST", skill)
        self.assertIn("DIAGNOSIS_MUST_BUY_A_DECISION", skill)
        self.assertIn("REGRESSION_FIRST", skill)
        self.assertIn("CONTINUOUS_HYGIENE_ACTIVE", skill)
        self.assertIn("FIRST_SUFFICIENT_SAFE_PATH_WINS", skill)
        self.assertIn("Progressive loading", skill)
        self.assertNotIn(
            "persist the authorization-only task commit before implementation", skill
        )

    def test_version_identity_is_coherent(self):
        leader = json.loads(
            (ROOT / "plugins/project-leader/plugin.json").read_text(encoding="utf-8")
        )
        guardian = json.loads(
            (ROOT / "plugins/recovery-guardian/plugin.json").read_text(encoding="utf-8")
        )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual("0.6.8", leader["version"])
        self.assertEqual("0.5.6", guardian["version"])
        self.assertIn("Unreleased — execution-first generation after 0.6.8 / 0.5.6", changelog)


if __name__ == "__main__":
    unittest.main()

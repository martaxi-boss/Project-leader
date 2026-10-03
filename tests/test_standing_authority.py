import json
import unittest
from pathlib import Path

from control.standing_authority import (
    CONTINUE_AUTONOMOUSLY,
    CONTINUE_REMEDIATION,
    EXCLUSIVE_HUMAN_INTERVENTION,
    HUMAN_GATE,
    NEW_UNCOVERED_MATERIAL_DECISION,
    STANDING_OWNER_GRANT,
    resolve_next_action,
)
from control.validate_records import validate_standing_authority

ROOT = Path(__file__).resolve().parents[1]


class StandingAuthorityTests(unittest.TestCase):
    def test_canonical_standing_authority_is_machine_valid(self):
        record = json.loads(
            (ROOT / "projects/standing-authority.json").read_text(encoding="utf-8")
        )
        self.assertTrue(validate_standing_authority(record))
        self.assertEqual(record["runtime_scope"], "PROJECT_LEADER_SKILL_RUNTIME")
        self.assertEqual(
            record["autonomy_rule"],
            "ALL_CANONICALLY_COVERED_EXECUTABLE_ACTIONS",
        )
        self.assertEqual(
            set(record["human_gate_conditions"]),
            {
                EXCLUSIVE_HUMAN_INTERVENTION,
                NEW_UNCOVERED_MATERIAL_DECISION,
            },
        )
        self.assertEqual(
            record["project_isolation"],
            "ONE_MUTABLE_TARGET_REPOSITORY_PER_TASK",
        )

    def test_merge_to_main_is_not_a_human_gate_by_action_name(self):
        decision = resolve_next_action(
            "merge_to_main",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=True,
        )
        self.assertEqual(decision["decision"], CONTINUE_AUTONOMOUSLY)
        self.assertEqual(decision["authority_source"], STANDING_OWNER_GRANT)

    def test_unsatisfied_controls_route_to_remediation_not_owner(self):
        decision = resolve_next_action(
            "merge_to_main",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=False,
        )
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["authority_source"], STANDING_OWNER_GRANT)

    def test_unavailable_system_action_requires_exclusive_human_intervention(self):
        decision = resolve_next_action(
            "repository_governance_change",
            canonical_effect_covered=True,
            system_can_execute=False,
            controls_satisfied=True,
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], EXCLUSIVE_HUMAN_INTERVENTION)

    def test_new_material_decision_requires_owner(self):
        decision = resolve_next_action(
            "change_architecture",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=True,
            new_material_decision=True,
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], NEW_UNCOVERED_MATERIAL_DECISION)

    def test_uncovered_effect_requires_new_material_decision(self):
        decision = resolve_next_action(
            "unknown_effect",
            canonical_effect_covered=False,
            system_can_execute=True,
            controls_satisfied=True,
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], NEW_UNCOVERED_MATERIAL_DECISION)


if __name__ == "__main__":
    unittest.main()

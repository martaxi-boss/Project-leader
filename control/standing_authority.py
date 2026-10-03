"""Deterministic standing-authority resolution for Project Leader.

This module does not grant project scope. It resolves whether a next action
already covered by canonical project state may continue autonomously under the
durable Owner standing grant, requires remediation first, or requires the Owner
because the next irreducible step is genuinely human/manual or a new material
decision.
"""

CONTINUE_AUTONOMOUSLY = "CONTINUE_AUTONOMOUSLY"
CONTINUE_REMEDIATION = "CONTINUE_REMEDIATION"
HUMAN_GATE = "HUMAN_GATE"

EXCLUSIVE_HUMAN_INTERVENTION = "EXCLUSIVE_HUMAN_INTERVENTION"
NEW_UNCOVERED_MATERIAL_DECISION = "NEW_UNCOVERED_MATERIAL_DECISION"
STANDING_OWNER_GRANT = "STANDING_OWNER_GRANT"


def resolve_next_action(
    action,
    *,
    canonical_effect_covered,
    system_can_execute,
    controls_satisfied,
    new_material_decision=False,
):
    """Resolve the next Project Leader action without action-name gates.

    Action names and effect classes do not create a Human Gate by themselves.
    The caller must already have reconstructed canonical project state.

    Returns a compact decision dictionary suitable for Supervisor/Recovery
    routing.
    """
    if not isinstance(action, str) or not action:
        raise ValueError("action must be a non-empty string")
    for name, value in (
        ("canonical_effect_covered", canonical_effect_covered),
        ("system_can_execute", system_can_execute),
        ("controls_satisfied", controls_satisfied),
        ("new_material_decision", new_material_decision),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")

    if new_material_decision or not canonical_effect_covered:
        return {
            "decision": HUMAN_GATE,
            "reason": NEW_UNCOVERED_MATERIAL_DECISION,
            "action": action,
            "authority_source": None,
        }

    if not system_can_execute:
        return {
            "decision": HUMAN_GATE,
            "reason": EXCLUSIVE_HUMAN_INTERVENTION,
            "action": action,
            "authority_source": None,
        }

    if not controls_satisfied:
        return {
            "decision": CONTINUE_REMEDIATION,
            "reason": "COVERED_CONTROLS_NOT_YET_SATISFIED",
            "action": action,
            "authority_source": STANDING_OWNER_GRANT,
        }

    return {
        "decision": CONTINUE_AUTONOMOUSLY,
        "reason": "COVERED_EXECUTABLE_ACTION",
        "action": action,
        "authority_source": STANDING_OWNER_GRANT,
    }

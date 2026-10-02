#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
EFFECTS = {
    "E0_READ_ONLY",
    "E1_RECOVERABLE_PROJECT_LOCAL",
    "E2_CONSEQUENTIAL_TRANSITION",
    "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED",
}
RESULTS = {"TERMINAL_SUCCESS", "BLOCKED", "HUMAN_GATE", "STALE_EXECUTION_PACKET"}

def _require(obj, keys):
    missing = [key for key in keys if key not in obj]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

def validate_task(record):
    _require(record, [
        "schema_version", "task_id", "project", "repository", "created_at",
        "authority", "starting_state", "effect_class", "mutation_scope",
        "allowed_actions", "prohibited_actions", "human_gates", "terminal_condition",
    ])
    if record["schema_version"] != "1.0":
        raise ValueError("unsupported schema_version")
    if not TASK_RE.fullmatch(record["task_id"]):
        raise ValueError("invalid task_id")
    if "/" not in record["repository"]:
        raise ValueError("repository must be owner/name")
    if record["effect_class"] not in EFFECTS:
        raise ValueError("invalid effect_class")
    if not record["mutation_scope"]:
        raise ValueError("mutation_scope must not be empty")
    state = record["starting_state"]
    _require(state, ["default_branch", "base_sha", "task_branch"])
    if not SHA_RE.fullmatch(state["base_sha"]):
        raise ValueError("invalid base_sha")
    authority = record["authority"]
    _require(authority, ["kind", "summary", "source"])
    for gate in record["human_gates"]:
        _require(gate, ["action", "requires_owner_approval"])
        if gate["requires_owner_approval"] is not True:
            raise ValueError("every human gate must require owner approval")
    privacy = record.get("privacy", {})
    if privacy.get("contains_secrets") is True or privacy.get("contains_private_conversation_text") is True:
        raise ValueError("durable records must not contain secrets or private conversation text")
    return True

def validate_result(record):
    _require(record, [
        "schema_version", "task_id", "terminal_status", "repository", "effect_class",
        "authorization_record", "implementation_head_sha", "branch", "changes",
        "validation", "material_non_effects", "residual_blockers",
    ])
    if record["schema_version"] != "1.0":
        raise ValueError("unsupported schema_version")
    if not TASK_RE.fullmatch(record["task_id"]):
        raise ValueError("invalid task_id")
    if record["terminal_status"] not in RESULTS:
        raise ValueError("invalid terminal_status")
    if record["effect_class"] not in EFFECTS:
        raise ValueError("invalid effect_class")
    if not SHA_RE.fullmatch(record["implementation_head_sha"]):
        raise ValueError("invalid implementation_head_sha")
    if not record["changes"]:
        raise ValueError("changes must not be empty")
    for item in record["validation"]:
        _require(item, ["name", "status"])
        if item["status"] not in {"PASS", "FAIL", "SKIPPED"}:
            raise ValueError("invalid validation status")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["task", "result"])
    parser.add_argument("path")
    args = parser.parse_args()
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    (validate_task if args.kind == "task" else validate_result)(data)
    print("VALID")

if __name__ == "__main__":
    main()

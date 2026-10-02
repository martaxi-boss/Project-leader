#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK_SCHEMA = ROOT / "task-authorization.schema.json"
RESULT_SCHEMA = ROOT / "worker-result.schema.json"
CHECKPOINT_SCHEMA = ROOT / "recovery-checkpoint.schema.json"
TRANSITION_AUTH_SCHEMA = ROOT / "transition-authorization.schema.json"
TRANSITION_RESULT_SCHEMA = ROOT / "transition-result.schema.json"

SUPPORTED_SCHEMA_KEYS = {
    "$schema", "$id", "title", "type", "additionalProperties", "required",
    "properties", "const", "enum", "pattern", "minLength", "maxLength",
    "minimum", "minItems", "uniqueItems", "items", "format"
}

def _load_schema(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    _assert_supported_schema(schema)
    return schema

def _assert_supported_schema(schema, path="$schema"):
    unknown = set(schema) - SUPPORTED_SCHEMA_KEYS
    if unknown:
        raise ValueError(f"{path}: unsupported schema keywords: {', '.join(sorted(unknown))}")
    for name, child in schema.get("properties", {}).items():
        _assert_supported_schema(child, f"{path}.properties.{name}")
    items = schema.get("items")
    if isinstance(items, dict):
        _assert_supported_schema(items, f"{path}.items")

def _is_type(value, expected):
    mapping = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if expected not in mapping:
        raise ValueError(f"unsupported JSON type: {expected}")
    return mapping[expected](value)

def _validate_datetime(value, path):
    if not isinstance(value, str):
        raise ValueError(f"{path}: date-time must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path}: invalid date-time") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{path}: date-time must include timezone")

def _validate(value, schema, path="$"):
    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, option) for option in options):
            raise ValueError(f"{path}: expected type {expected}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value not in enum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path}: longer than maxLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(f"{path}: does not match pattern")
        if schema.get("format") == "date-time":
            _validate_datetime(value, path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: below minimum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path}: fewer than minItems")
        if schema.get("uniqueItems"):
            canonical = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(canonical) != len(set(canonical)):
                raise ValueError(f"{path}: duplicate items are not allowed")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"{path}: missing required fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ValueError(f"{path}: unknown fields: {', '.join(sorted(unknown))}")
        for name, child_schema in properties.items():
            if name in value:
                _validate(value[name], child_schema, f"{path}.{name}")

def _reject_duplicate_names(items, label):
    names = [item["name"] for item in items]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label} names are not allowed: {', '.join(duplicates)}")

def validate_task(record):
    _validate(record, _load_schema(TASK_SCHEMA))
    return True

def validate_result(record):
    _validate(record, _load_schema(RESULT_SCHEMA))
    _reject_duplicate_names(record["validation"], "validation")
    _reject_duplicate_names(record.get("ci", []), "CI")
    if record["terminal_status"] == "TERMINAL_SUCCESS":
        failed = [item["name"] for item in record["validation"] if item["status"] == "FAIL"]
        if failed:
            raise ValueError("terminal success cannot contain failed validation: " + ", ".join(failed))
        passed = [item["name"] for item in record["validation"] if item["status"] == "PASS"]
        if not passed:
            raise ValueError("terminal success requires at least one positive validation PASS")
        missing_evidence = [
            item["name"] for item in record["validation"]
            if item["status"] in {"PASS", "SKIPPED"} and not item.get("evidence")
        ]
        if missing_evidence:
            raise ValueError("terminal success requires evidence/justification for PASS or SKIPPED validation: " + ", ".join(missing_evidence))
        bad_ci = [item["name"] for item in record.get("ci", []) if item["status"] in {"FAILURE", "PENDING"}]
        if bad_ci:
            raise ValueError("terminal success cannot contain failing/pending CI: " + ", ".join(bad_ci))
    return True

def _require_named_status(items, required_names, expected_status, label):
    by_name = {item["name"]: item for item in items}
    missing = [name for name in required_names if name not in by_name]
    if missing:
        raise ValueError(f"required {label} missing: {', '.join(missing)}")
    wrong = [name for name in required_names if by_name[name]["status"] != expected_status]
    if wrong:
        raise ValueError(f"required {label} must be {expected_status}: " + ", ".join(wrong))

def validate_pair(task, result):
    validate_task(task)
    validate_result(result)
    checks = {
        "task_id": (task["task_id"], result["task_id"]),
        "repository": (task["repository"], result["repository"]),
        "effect_class": (task["effect_class"], result["effect_class"]),
        "branch": (task["starting_state"]["task_branch"], result["branch"]),
        "authorization_record": (f".project-leader/tasks/{task['task_id']}.json", result["authorization_record"]),
    }
    for name, (expected, actual) in checks.items():
        if expected != actual:
            raise ValueError(f"task/result mismatch for {name}: expected {expected!r}, got {actual!r}")
    expected_pr = task["starting_state"].get("pr_number")
    if expected_pr is not None and result.get("pr_number") != expected_pr:
        raise ValueError(f"task/result mismatch for pr_number: expected {expected_pr!r}, got {result.get('pr_number')!r}")
    if result["terminal_status"] == "TERMINAL_SUCCESS":
        _require_named_status(result["validation"], task.get("required_validation", []), "PASS", "validation")
        _require_named_status(result.get("ci", []), task.get("required_ci", []), "SUCCESS", "CI")
    return True

def _normalize_changed_path(path):
    normalized = path.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
        raise ValueError(f"invalid changed path: {path!r}")
    return normalized

def validate_scope(task, changed_files):
    validate_task(task)
    if not changed_files:
        raise ValueError("scope validation requires at least one changed file")
    patterns = task["mutation_scope"]
    normalized = [_normalize_changed_path(path) for path in changed_files]
    outside = [path for path in normalized if not any(fnmatchcase(path, pattern) for pattern in patterns)]
    if outside:
        raise ValueError("changed files outside authorized mutation_scope: " + ", ".join(sorted(outside)))
    return True

def validate_checkpoint(record):
    _validate(record, _load_schema(CHECKPOINT_SCHEMA))
    if record["attempt_count"] > 3:
        raise ValueError("recovery checkpoint attempt_count cannot exceed 3 for one action fingerprint")
    if record["identical_failure_count"] > 2:
        raise ValueError("recovery checkpoint identical_failure_count cannot exceed 2 before replan")
    if record["no_progress_iterations"] > 3:
        raise ValueError("recovery checkpoint no_progress_iterations cannot exceed 3")
    return True

def validate_transition_authorization(record):
    _validate(record, _load_schema(TRANSITION_AUTH_SCHEMA))
    return True

def validate_transition_result(record):
    _validate(record, _load_schema(TRANSITION_RESULT_SCHEMA))
    status = record["terminal_status"]
    authorization_record = record["authorization_record"]
    if status == "SUCCESS" and not authorization_record:
        raise ValueError("successful Human-Gate transition requires a durable authorization_record")
    if status == "HISTORICAL_OBSERVED":
        if authorization_record is not None:
            raise ValueError("historical observed transition must not invent an authorization_record")
        if not record["residual_blockers"]:
            raise ValueError("historical observed transition must record the authorization-evidence gap")
    return True

def validate_transition_pair(authorization, result):
    validate_transition_authorization(authorization)
    validate_transition_result(result)
    if result["terminal_status"] != "SUCCESS":
        raise ValueError("transition pair certification is only valid for SUCCESS results")
    checks = {
        "transition_id": (authorization["transition_id"], result["transition_id"]),
        "task_id": (authorization["task_id"], result["task_id"]),
        "repository": (authorization["repository"], result["repository"]),
        "action": (authorization["action"], result["action"]),
        "target": (authorization["target"], result["target"]),
        "authorization_record": (
            f".project-leader/transitions/{authorization['transition_id']}.authorization.json",
            result["authorization_record"],
        ),
    }
    for name, (expected, actual) in checks.items():
        if expected != actual:
            raise ValueError(f"transition authorization/result mismatch for {name}: expected {expected!r}, got {actual!r}")
    return True

def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["task","result","pair","scope","checkpoint","transition-auth","transition-result","transition-pair"])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.kind == "pair":
        if len(args.paths) != 2:
            parser.error("pair requires TASK_PATH RESULT_PATH")
        validate_pair(_read_json(args.paths[0]), _read_json(args.paths[1]))
    elif args.kind == "scope":
        if len(args.paths) < 2:
            parser.error("scope requires TASK_PATH CHANGED_FILE [CHANGED_FILE ...]")
        validate_scope(_read_json(args.paths[0]), args.paths[1:])
    elif args.kind == "transition-pair":
        if len(args.paths) != 2:
            parser.error("transition-pair requires AUTHORIZATION_PATH RESULT_PATH")
        validate_transition_pair(_read_json(args.paths[0]), _read_json(args.paths[1]))
    else:
        if len(args.paths) != 1:
            parser.error(f"{args.kind} requires exactly one path")
        data = _read_json(args.paths[0])
        validators = {
            "task": validate_task,
            "result": validate_result,
            "checkpoint": validate_checkpoint,
            "transition-auth": validate_transition_authorization,
            "transition-result": validate_transition_result,
        }
        validators[args.kind](data)
    print("VALID")

if __name__ == "__main__":
    main()

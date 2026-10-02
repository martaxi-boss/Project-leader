#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK_SCHEMA = ROOT / "task-authorization.schema.json"
RESULT_SCHEMA = ROOT / "worker-result.schema.json"

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

def validate_task(record):
    _validate(record, _load_schema(TASK_SCHEMA))
    return True

def validate_result(record):
    _validate(record, _load_schema(RESULT_SCHEMA))
    if record["terminal_status"] == "TERMINAL_SUCCESS":
        failed = [item["name"] for item in record["validation"] if item["status"] == "FAIL"]
        if failed:
            raise ValueError("terminal success cannot contain failed validation: " + ", ".join(failed))
        bad_ci = [
            item["name"] for item in record.get("ci", [])
            if item["status"] in {"FAILURE", "PENDING"}
        ]
        if bad_ci:
            raise ValueError("terminal success cannot contain failing/pending CI: " + ", ".join(bad_ci))
    return True

def validate_pair(task, result):
    validate_task(task)
    validate_result(result)

    checks = {
        "task_id": (task["task_id"], result["task_id"]),
        "repository": (task["repository"], result["repository"]),
        "effect_class": (task["effect_class"], result["effect_class"]),
        "branch": (task["starting_state"]["task_branch"], result["branch"]),
        "authorization_record": (
            f".project-leader/tasks/{task['task_id']}.json",
            result["authorization_record"],
        ),
    }
    for name, (expected, actual) in checks.items():
        if expected != actual:
            raise ValueError(f"task/result mismatch for {name}: expected {expected!r}, got {actual!r}")

    expected_pr = task["starting_state"].get("pr_number")
    if expected_pr is not None and result.get("pr_number") != expected_pr:
        raise ValueError(
            f"task/result mismatch for pr_number: expected {expected_pr!r}, got {result.get('pr_number')!r}"
        )
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["task", "result", "pair"])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    if args.kind == "pair":
        if len(args.paths) != 2:
            parser.error("pair requires TASK_PATH RESULT_PATH")
        task = json.loads(Path(args.paths[0]).read_text(encoding="utf-8"))
        result = json.loads(Path(args.paths[1]).read_text(encoding="utf-8"))
        validate_pair(task, result)
    else:
        if len(args.paths) != 1:
            parser.error(f"{args.kind} requires exactly one path")
        data = json.loads(Path(args.paths[0]).read_text(encoding="utf-8"))
        (validate_task if args.kind == "task" else validate_result)(data)

    print("VALID")

if __name__ == "__main__":
    main()

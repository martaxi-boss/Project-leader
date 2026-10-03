#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control.validate_records import validate_recovery_journal, validate_result


def api_get(url, token):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "project-leader-evidence-verifier",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))



def ci_run_requires_recovery_journal(payload):
    attempt = payload.get("run_attempt", 1)
    return isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 1


def verify_recovery_journal_records(result, records):
    if not records:
        raise ValueError("CI retry requires a durable append-only recovery journal")
    validate_recovery_journal(records)
    for record in records:
        if record.get("task_id") != result.get("task_id"):
            raise ValueError("recovery journal task_id does not match Worker Result")
        if record.get("repository") != result.get("repository"):
            raise ValueError("recovery journal repository does not match Worker Result")

    events = {record.get("event") for record in records}
    for required in ("FAILURE_OBSERVED", "RETRY_AUTHORIZED"):
        if required not in events:
            raise ValueError(f"recovery journal is missing required event: {required}")
    if result.get("terminal_status") == "TERMINAL_SUCCESS" and "RECOVERED" not in events:
        raise ValueError("successful retry requires a RECOVERED recovery event")
    return True


def load_recovery_journal(result, repository, token, current_head_sha, api_base):
    directory = f".project-leader/recovery-events/{result['task_id']}"
    quoted_directory = urllib.parse.quote(directory, safe="/")
    try:
        listing = api_get(
            f"{api_base}/repos/{repository}/contents/{quoted_directory}?ref={current_head_sha}",
            token,
        )
    except Exception as exc:
        raise ValueError("CI retry requires a durable append-only recovery journal") from exc

    if not isinstance(listing, list):
        raise ValueError("recovery journal path is not a directory")

    records = []
    for item in sorted(listing, key=lambda entry: entry.get("name", "")):
        name = item.get("name", "")
        if item.get("type") != "file" or not name.endswith(".json"):
            continue
        quoted_name = urllib.parse.quote(name, safe="")
        payload = api_get(
            f"{api_base}/repos/{repository}/contents/{quoted_directory}/{quoted_name}?ref={current_head_sha}",
            token,
        )
        if payload.get("encoding") != "base64":
            raise ValueError("recovery journal contents payload is not base64")
        raw = base64.b64decode(payload.get("content", "").encode("ascii"))
        records.append(json.loads(raw.decode("utf-8")))

    verify_recovery_journal_records(result, records)
    return True

def verify_run_payload(ci_item, result, payload, repository):
    if ci_item["status"] != "SUCCESS":
        raise ValueError(f"required CI evidence is not SUCCESS: {ci_item['name']}")
    if payload.get("name") != ci_item["name"]:
        raise ValueError(f"workflow name mismatch for run {ci_item['run_id']}")
    if payload.get("head_sha") != result["implementation_head_sha"]:
        raise ValueError(f"workflow SHA mismatch for run {ci_item['run_id']}")
    if payload.get("status") != "completed" or payload.get("conclusion") != "success":
        raise ValueError(f"workflow run {ci_item['run_id']} is not completed/success")
    run_repo = (payload.get("repository") or {}).get("full_name")
    if run_repo != repository:
        raise ValueError(f"workflow repository mismatch for run {ci_item['run_id']}")
    return True


def verify_authorization_payloads(result, authorization_payload, current_payload, ancestry_payload):
    expected_digest = result.get("authorization_sha256")
    authorization_commit_sha = result.get("authorization_commit_sha")
    if not expected_digest or not authorization_commit_sha:
        return True

    def decode(payload):
        if payload.get("encoding") != "base64":
            raise ValueError("authorization contents payload is not base64")
        return base64.b64decode(payload.get("content", "").encode("ascii"))

    authorization_bytes = decode(authorization_payload)
    current_bytes = decode(current_payload)
    if hashlib.sha256(authorization_bytes).hexdigest() != expected_digest:
        raise ValueError("authorization_sha256 does not match Task Authorization at authorization_commit_sha")
    if hashlib.sha256(current_bytes).hexdigest() != expected_digest:
        raise ValueError("Task Authorization changed after the bound authorization commit")

    if ancestry_payload.get("status") not in {"ahead", "identical"}:
        raise ValueError("authorization_commit_sha is not an ancestor of implementation_head_sha")
    if (ancestry_payload.get("base_commit") or {}).get("sha") != authorization_commit_sha:
        raise ValueError("authorization ancestry base_commit mismatch")
    if result.get("terminal_status") == "TERMINAL_SUCCESS" and ancestry_payload.get("status") != "ahead":
        raise ValueError("terminal success requires implementation after the authorization-only commit")
    return True


def verify_compare_payload(payload, implementation_head_sha, current_head_sha):
    if payload.get("status") not in {"ahead", "identical"}:
        raise ValueError("implementation_head_sha is not an ancestor of the current PR head")
    base_sha = (payload.get("base_commit") or {}).get("sha")
    if base_sha != implementation_head_sha:
        raise ValueError("compare response base_commit does not match implementation_head_sha")
    head_sha = ((payload.get("commits") or [{}])[-1]).get("sha") if payload.get("commits") else implementation_head_sha
    if payload.get("status") == "ahead" and head_sha != current_head_sha:
        raise ValueError("compare response does not terminate at current PR head")
    if payload.get("status") == "identical" and implementation_head_sha != current_head_sha:
        raise ValueError("identical compare requires implementation head to equal current head")
    return True


def verify_github_evidence(result, repository, token, current_head_sha, api_base="https://api.github.com"):
    validate_result(result)
    if result["schema_version"] != "2.0":
        raise ValueError("external GitHub evidence verification requires Worker Result schema_version 2.0")
    if result["repository"] != repository:
        raise ValueError("Worker Result repository does not match verifier repository")

    authorization_commit_sha = result.get("authorization_commit_sha")
    authorization_sha256 = result.get("authorization_sha256")
    if bool(authorization_commit_sha) != bool(authorization_sha256):
        raise ValueError("authorization_commit_sha and authorization_sha256 must be provided together")
    if authorization_commit_sha:
        path = result["authorization_record"]
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("authorization_record is not a safe repository-relative path")
        quoted_path = urllib.parse.quote(path, safe="/")
        authorization_payload = api_get(
            f"{api_base}/repos/{repository}/contents/{quoted_path}?ref={authorization_commit_sha}",
            token,
        )
        current_payload = api_get(
            f"{api_base}/repos/{repository}/contents/{quoted_path}?ref={current_head_sha}",
            token,
        )
        ancestry_payload = api_get(
            f"{api_base}/repos/{repository}/compare/{authorization_commit_sha}...{result['implementation_head_sha']}",
            token,
        )
        verify_authorization_payloads(result, authorization_payload, current_payload, ancestry_payload)

    run_payloads = []
    for ci_item in result["ci"]:
        run_id = ci_item.get("run_id")
        if not isinstance(run_id, int):
            raise ValueError(f"CI run_id missing for {ci_item['name']}")
        payload = api_get(f"{api_base}/repos/{repository}/actions/runs/{run_id}", token)
        verify_run_payload(ci_item, result, payload, repository)
        run_payloads.append(payload)

    if any(ci_run_requires_recovery_journal(payload) for payload in run_payloads):
        load_recovery_journal(result, repository, token, current_head_sha, api_base)

    compare = api_get(
        f"{api_base}/repos/{repository}/compare/{result['implementation_head_sha']}...{current_head_sha}",
        token,
    )
    verify_compare_payload(compare, result["implementation_head_sha"], current_head_sha)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-head-sha", required=True)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--api-base", default="https://api.github.com")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"missing token environment variable: {args.token_env}")
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    verify_github_evidence(result, args.repository, token, args.current_head_sha, args.api_base)
    print("GITHUB_EVIDENCE_VALID")


if __name__ == "__main__":
    main()

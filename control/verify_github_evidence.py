#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control.validate_records import validate_result


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

    for ci_item in result["ci"]:
        run_id = ci_item.get("run_id")
        if not isinstance(run_id, int):
            raise ValueError(f"CI run_id missing for {ci_item['name']}")
        payload = api_get(f"{api_base}/repos/{repository}/actions/runs/{run_id}", token)
        verify_run_payload(ci_item, result, payload, repository)

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

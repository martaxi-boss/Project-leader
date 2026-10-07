import json
import tempfile
import unittest
from pathlib import Path

from control.runtime_bootstrap import MIN_LOADER_VERSION, pin_runtime_bundle
from control.standing_authority import (
    RECOVERY_REPLAN_REQUIRED,
    resolve_recovery_action,
)
from control.trusted_gate import verify_pr_evidence_context
from control.validate_records import (
    canonical_sha256,
    validate_recovery_journal,
    validate_transition_result,
)
from control.verify_github_evidence import (
    PROJECT_LEADER_TRUSTED_WORKFLOWS,
    verify_authorization_only_history,
    verify_recovery_journal_records,
    verify_run_payload,
)
from scripts.package_plugins import build, validate_plugin_tree


def recovery_event(
    sequence,
    kind,
    *,
    fingerprint="A",
    strategy=1,
    attempt=1,
    identical=1,
    no_progress=1,
    previous=None,
):
    return {
        "schema_version": "1.0",
        "task_id": "TASK-P1-001",
        "repository": "owner/repo",
        "sequence": sequence,
        "recorded_at": f"2026-10-07T09:{sequence:02d}:00Z",
        "event": kind,
        "strategy_generation": strategy,
        "action_fingerprint": fingerprint,
        "attempt_count": attempt,
        "identical_failure_count": identical,
        "no_progress_iterations": no_progress,
        "previous_event_sha256": previous,
        "detail": "audit regression",
    }


def write_plugin(root, name):
    plugin = root / "plugins" / name
    skill = plugin / "skills" / name
    (skill / "agents").mkdir(parents=True)
    (skill / "references").mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": "1.0.0",
                "skills": "./skills/",
                "extensions": {"com.openai": {"apps": "./.app.json"}},
            }
        ),
        encoding="utf-8",
    )
    (plugin / ".app.json").write_text(
        json.dumps(
            {
                "apps": {
                    "github": {
                        "id": "connector_test",
                        "required": True,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (skill / "agents" / "openai.yaml").write_text("name: test\n", encoding="utf-8")
    (skill / "references" / "recovery-protocol.md").write_text(
        "# Recovery\n", encoding="utf-8"
    )
    return plugin


class AuditP1RegressionTests(unittest.TestCase):
    def test_pr_file_api_limit_fails_closed(self):
        changes = [{"filename": f"f/{i}"} for i in range(3000)]
        with self.assertRaisesRegex(ValueError, "3000-file limit"):
            verify_pr_evidence_context(
                declared_changed_count=3000,
                observed_changes=changes,
                event_base_sha="a" * 40,
                live_base_sha="a" * 40,
            )

    def test_pr_file_count_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify_pr_evidence_context(
                declared_changed_count=2,
                observed_changes=[{"filename": "one"}],
                event_base_sha="a" * 40,
                live_base_sha="a" * 40,
            )

    def test_stale_base_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "base is stale"):
            verify_pr_evidence_context(
                declared_changed_count=1,
                observed_changes=[{"filename": "one"}],
                event_base_sha="a" * 40,
                live_base_sha="b" * 40,
            )

    def test_homonymous_workflow_cannot_substitute_required_identity(self):
        result = {"implementation_head_sha": "a" * 40}
        ci = {"name": "Control contract tests", "status": "SUCCESS", "run_id": 1}
        payload = {
            "id": 1,
            "name": "Control contract tests",
            "workflow_id": 999999999,
            "path": ".github/workflows/unrelated.yml",
            "event": "pull_request",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "martaxi-boss/Project-leader"},
        }
        with self.assertRaisesRegex(ValueError, "workflow id mismatch"):
            verify_run_payload(
                ci,
                result,
                payload,
                "martaxi-boss/Project-leader",
                PROJECT_LEADER_TRUSTED_WORKFLOWS["Control contract tests"],
            )

    def test_authorization_commit_with_implementation_is_rejected(self):
        task = {"starting_state": {"base_sha": "a" * 40}}
        result = {
            "authorization_commit_sha": "b" * 40,
            "authorization_record": ".project-leader/tasks/TASK-P1-001.json",
        }
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {"filename": ".project-leader/tasks/TASK-P1-001.json"},
                {"filename": "src/app.py"},
            ],
        }
        with self.assertRaisesRegex(ValueError, "only the Task Authorization"):
            verify_authorization_only_history(task, result, payload)

    def test_interleaved_action_cannot_reset_retry_counters(self):
        first = recovery_event(1, "FAILURE_OBSERVED", fingerprint="A", attempt=2)
        second = recovery_event(
            2,
            "FAILURE_OBSERVED",
            fingerprint="B",
            attempt=1,
            previous=canonical_sha256(first),
        )
        third = recovery_event(
            3,
            "FAILURE_OBSERVED",
            fingerprint="A",
            attempt=1,
            previous=canonical_sha256(second),
        )
        with self.assertRaisesRegex(ValueError, "cannot decrease"):
            validate_recovery_journal([first, second, third])

    def test_retry_authorization_must_increment_attempt(self):
        first = recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = recovery_event(
            2,
            "RETRY_AUTHORIZED",
            attempt=2,
            previous=canonical_sha256(first),
        )
        third = recovery_event(
            3,
            "RETRY_AUTHORIZED",
            attempt=2,
            previous=canonical_sha256(second),
        )
        with self.assertRaisesRegex(ValueError, "strictly increase"):
            validate_recovery_journal([first, second, third])

    def test_replan_journal_is_valid_without_fictitious_retry(self):
        first = recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = recovery_event(
            2,
            "REPLAN",
            strategy=2,
            attempt=0,
            identical=0,
            no_progress=0,
            previous=canonical_sha256(first),
        )
        result = {
            "task_id": "TASK-P1-001",
            "repository": "owner/repo",
            "terminal_status": "BLOCKED",
        }
        self.assertTrue(
            verify_recovery_journal_records(
                result, [first, second], require_retry=False
            )
        )

    def test_failed_transition_requires_authorization_and_blocker(self):
        record = {
            "schema_version": "1.0",
            "transition_id": "TASK-P1-001-DEPLOY",
            "task_id": "TASK-P1-001",
            "repository": "owner/repo",
            "terminal_status": "FAILURE",
            "authorization_record": None,
            "action": "deploy",
            "target": {
                "kind": "environment",
                "identifier": "test",
                "revision": None,
                "base_revision": None,
                "environment": "test",
            },
            "observed_at": "2026-10-07T09:00:00Z",
            "final_state": {"status": "FAILED", "revision": None},
            "evidence": ["provider rejected request"],
            "residual_blockers": ["provider error"],
        }
        with self.assertRaisesRegex(ValueError, "authorization_record"):
            validate_transition_result(record)

    def test_success_transition_cannot_retain_blocker(self):
        record = {
            "schema_version": "1.0",
            "transition_id": "TASK-P1-001-MERGE",
            "task_id": "TASK-P1-001",
            "repository": "owner/repo",
            "terminal_status": "SUCCESS",
            "authorization_record": ".project-leader/transitions/TASK-P1-001-MERGE.authorization.json",
            "action": "merge_to_main",
            "target": {
                "kind": "pull_request",
                "identifier": "#1",
                "revision": "b" * 40,
                "base_revision": "a" * 40,
                "environment": None,
            },
            "observed_at": "2026-10-07T09:00:00Z",
            "final_state": {"status": "MERGED", "revision": "c" * 40},
            "evidence": ["merged"],
            "residual_blockers": ["contradiction"],
        }
        with self.assertRaisesRegex(ValueError, "cannot retain residual blockers"):
            validate_transition_result(record)

    def test_package_rejects_unexpected_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = write_plugin(root, "project-leader")
            (plugin / ".env").write_text("SECRET=x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected package files"):
                validate_plugin_tree(plugin, "project-leader")

    def test_package_rejects_external_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = write_plugin(root, "project-leader")
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (plugin / "leak").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                validate_plugin_tree(plugin, "project-leader")

    def test_package_manifest_binds_source_revision_and_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plugin(root, "project-leader")
            write_plugin(root, "recovery-guardian")
            manifest = build(
                root,
                root / "dist",
                source_revision="a" * 40,
                build_run_id="12345",
            )
            self.assertEqual("2.0", manifest["schema_version"])
            self.assertEqual("a" * 40, manifest["provenance"]["source_revision"])
            self.assertEqual("12345", manifest["provenance"]["build_run_id"])
            self.assertTrue(all(item["contents"] for item in manifest["plugins"]))


    def test_recovery_resolver_enforces_attempt_budget(self):
        decision = resolve_recovery_action(
            objective_authorized=True,
            standing_delegation_valid=True,
            effect_class="E1_RECOVERABLE_PROJECT_LOCAL",
            same_project_workstream=True,
            same_action_retry=True,
            retry_basis="NEW_EVIDENCE",
            attempt_count=3,
        )
        self.assertEqual(RECOVERY_REPLAN_REQUIRED, decision["decision"])
        self.assertEqual("ATTEMPT_LIMIT_REACHED", decision["reason"])

    def test_recovery_resolver_enforces_identical_failure_budget(self):
        decision = resolve_recovery_action(
            objective_authorized=True,
            standing_delegation_valid=True,
            effect_class="E1_RECOVERABLE_PROJECT_LOCAL",
            same_project_workstream=True,
            same_action_retry=True,
            retry_basis="NEW_EVIDENCE",
            attempt_count=2,
            identical_failure_count=2,
        )
        self.assertEqual(RECOVERY_REPLAN_REQUIRED, decision["decision"])
        self.assertEqual("IDENTICAL_FAILURE_LIMIT_REACHED", decision["reason"])

    def test_runtime_bootstrap_pins_one_revision_for_every_read(self):
        calls = {"resolve": 0, "refs": []}

        def resolve():
            calls["resolve"] += 1
            return "a" * 40

        def read(path, revision):
            calls["refs"].append((path, revision))
            return path

        bundle = pin_runtime_bundle(
            resolve,
            read,
            loader_version=MIN_LOADER_VERSION,
            paths=("one", "two", "three"),
        )
        self.assertEqual(1, calls["resolve"])
        self.assertEqual("a" * 40, bundle["revision"])
        self.assertEqual({"a" * 40}, {ref for _, ref in calls["refs"]})

    def test_runtime_bootstrap_rejects_incompatible_loader(self):
        with self.assertRaisesRegex(ValueError, "minimum"):
            pin_runtime_bundle(
                lambda: "a" * 40,
                lambda path, revision: path,
                loader_version=MIN_LOADER_VERSION - 1,
                paths=("one",),
            )


if __name__ == "__main__":
    unittest.main()

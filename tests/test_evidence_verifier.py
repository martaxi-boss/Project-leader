import base64
import hashlib
import unittest

from control.verify_github_evidence import (
    ci_run_requires_recovery_journal,
    verify_authorization_payloads,
    verify_compare_payload,
    verify_recovery_journal_records,
    verify_run_payload,
)


class EvidenceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.repository = "martaxi-boss/Project-leader"
        self.result = {
            "implementation_head_sha": "a" * 40,
        }
        self.ci = {"name": "Control contract tests", "status": "SUCCESS", "run_id": 123}
        self.run = {
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": self.repository},
        }

    def test_matching_run_is_accepted(self):
        self.assertTrue(verify_run_payload(self.ci, self.result, self.run, self.repository))

    def test_wrong_sha_is_rejected(self):
        self.run["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_failed_run_is_rejected(self):
        self.run["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_wrong_workflow_name_is_rejected(self):
        self.run["name"] = "Other"
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_ancestor_compare_is_accepted(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
        }
        self.assertTrue(verify_compare_payload(payload, "a" * 40, "b" * 40))

    def test_diverged_compare_is_rejected(self):
        payload = {"status": "diverged", "base_commit": {"sha": "a" * 40}, "commits": []}
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40)

    def recovery_event(self, sequence, kind, previous=None, attempt=1):
        return {
            "schema_version": "1.0",
            "task_id": "TASK-001",
            "repository": self.repository,
            "sequence": sequence,
            "recorded_at": f"2026-10-03T01:0{sequence}:00Z",
            "event": kind,
            "strategy_generation": 1,
            "action_fingerprint": "ci|android|rerun",
            "attempt_count": attempt,
            "identical_failure_count": 1,
            "no_progress_iterations": 1,
            "previous_event_sha256": previous,
            "detail": "test recovery",
        }

    def test_run_attempt_two_requires_recovery_journal(self):
        self.assertFalse(ci_run_requires_recovery_journal({"run_attempt": 1}))
        self.assertTrue(ci_run_requires_recovery_journal({"run_attempt": 2}))

    def test_retry_requires_valid_recovery_journal(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        self.assertTrue(verify_recovery_journal_records(result, [first, second, third]))

    def test_successful_retry_without_recovered_event_fails(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        with self.assertRaises(ValueError):
            verify_recovery_journal_records(result, [first, second])

    def auth_payload(self, raw):
        return {
            "encoding": "base64",
            "content": base64.b64encode(raw).decode("ascii"),
        }

    def test_immutable_authorization_binding_is_accepted(self):
        raw = b'{"task_id":"TASK-001"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "ahead",
            "base_commit": {"sha": "c" * 40},
            "commits": [{"sha": "a" * 40}],
        }
        self.assertTrue(
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(raw),
                ancestry,
            )
        )

    def test_changed_authorization_after_binding_is_rejected(self):
        raw = b'{"task_id":"TASK-001"}\n'
        changed = b'{"task_id":"TASK-001","scope":"wider"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "ahead",
            "base_commit": {"sha": "c" * 40},
            "commits": [{"sha": "a" * 40}],
        }
        with self.assertRaises(ValueError):
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(changed),
                ancestry,
            )

    def test_terminal_success_requires_work_after_authorization_commit(self):
        raw = b'{"task_id":"TASK-001"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "identical",
            "base_commit": {"sha": "c" * 40},
            "commits": [],
        }
        with self.assertRaises(ValueError):
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(raw),
                ancestry,
            )


if __name__ == "__main__":
    unittest.main()

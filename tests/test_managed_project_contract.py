import unittest
from datetime import datetime, timezone

from control.managed_project_contract import (
    classify_external_ci,
    validate_managed_result,
    validate_managed_task,
)


REPOSITORY = "owner/project"


def task(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "repository": REPOSITORY,
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "required_ci": ["Project CI"],
    }


def result(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "repository": REPOSITORY,
        "terminal_status": "TERMINAL_SUCCESS",
        "ci": [{"name": "Project CI", "status": "SUCCESS", "run_id": 123}],
    }


class ManagedProjectContractTests(unittest.TestCase):
    def test_new_managed_task_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_task(task("1.0"), REPOSITORY)

    def test_managed_task_requires_append_only_recovery(self):
        item = task()
        item["recovery"]["mode"] = "MUTABLE_CHECKPOINT"
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY)

    def test_managed_task_requires_ci(self):
        item = task()
        item["required_ci"] = []
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY)

    def test_managed_result_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_result(task(), result("1.0"), REPOSITORY)

    def test_terminal_success_requires_real_run_id(self):
        item = result()
        item["ci"][0]["run_id"] = None
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY)

    def test_recent_in_progress_ci_is_wait_not_failure(self):
        run = {
            "status": "in_progress",
            "conclusion": None,
            "updated_at": "2026-10-03T00:25:12Z",
        }
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "WAITING_EXTERNAL_CI")

    def test_old_in_progress_ci_requires_investigation_not_retry(self):
        run = {
            "status": "in_progress",
            "conclusion": None,
            "updated_at": "2026-10-02T22:00:00Z",
        }
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "INVESTIGATE_STALE_CI")

    def test_completed_success_is_terminal_success(self):
        self.assertEqual(
            classify_external_ci({"status": "completed", "conclusion": "success"}),
            "COMPLETED_SUCCESS",
        )


if __name__ == "__main__":
    unittest.main()

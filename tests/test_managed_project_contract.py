import unittest
from datetime import datetime, timezone

from control.managed_project_contract import (
    classify_external_ci,
    decide_ci_dispatch,
    reconcile_external_ci_wait,
    reconcile_legacy_checkpoint_liveness,
    validate_managed_result,
    validate_managed_task,
)

REPOSITORY = "owner/project"
CONTROL_REPOSITORY = "owner/control"


def task(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "project": "TEST",
        "repository": REPOSITORY,
        "created_at": "2026-10-03T01:00:00Z",
        "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "bounded managed task",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/task-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["src/**", ".project-leader/tasks/**", ".project-leader/results/**"],
        "allowed_actions": ["create_branch", "edit_project_files", "create_commits", "run_ci", "open_or_update_pull_request"],
        "prohibited_actions": ["merge_to_main"],
        "human_gates": [{"action": "merge_to_main", "requires_owner_approval": True}],
        "required_validation": ["Mutation scope audit", "GitHub evidence verification"],
        "required_ci": ["Project CI"],
        "policy": {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "repository": CONTROL_REPOSITORY,
            "revision": "c" * 40,
            "sha256": "d" * 64,
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "green PR",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }


def legacy_checkpoint(status="ACTIVE"):
    return {
        "schema_version": "1.0",
        "task_id": "LEGACY-TASK-001",
        "repository": REPOSITORY,
        "updated_at": "2026-10-03T01:00:00Z",
        "last_durable_step": "legacy step",
        "action_fingerprint": "legacy|task|ci",
        "attempt_count": 1,
        "identical_failure_count": 0,
        "no_progress_iterations": 0,
        "strategy": "legacy recovery",
        "strategy_generation": 1,
        "last_error": None,
        "next_step": "inspect current durable state",
        "status": status,
    }


def result(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "repository": REPOSITORY,
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "authorization_record": ".project-leader/tasks/TASK-001.json",
        "authorization_commit_sha": "b" * 40,
        "authorization_sha256": "e" * 64,
        "implementation_head_sha": "f" * 40,
        "branch": "builder/task-001",
        "terminal_status": "TERMINAL_SUCCESS",
        "changes": ["src/app.py"],
        "validation": [{"name": "Mutation scope audit", "status": "PASS", "evidence": "diff checked"}],
        "ci": [{"name": "Project CI", "status": "SUCCESS", "run_id": 123}],
        "material_non_effects": ["no merge"],
        "residual_blockers": [],
    }


class ManagedProjectContractTests(unittest.TestCase):
    def test_new_managed_task_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_task(task("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_central_policy_binding(self):
        item = task()
        item["policy"] = {
            "binding_mode": "LOCAL_BASE_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "base_sha": "a" * 40,
            "sha256": "d" * 64,
        }
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_immutable_authorization(self):
        item = task()
        del item["integrity_mode"]
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_append_only_recovery(self):
        item = task()
        item["recovery"]["mode"] = "MUTABLE_CHECKPOINT"
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_ci(self):
        item = task()
        item["required_ci"] = []
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_result(task(), result("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_requires_authorization_binding(self):
        item = result()
        del item["authorization_sha256"]
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_terminal_success_requires_real_run_id(self):
        item = result()
        item["ci"][0]["run_id"] = None
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_legacy_active_checkpoint_without_live_workstream_is_stale(self):
        state = reconcile_legacy_checkpoint_liveness(legacy_checkpoint())
        self.assertEqual(state["state"], "STALE_LEGACY_CHECKPOINT")
        self.assertFalse(state["actionable"])

    def test_legacy_active_checkpoint_with_live_branch_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_live_branch=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")
        self.assertTrue(state["actionable"])

    def test_legacy_active_checkpoint_with_open_pr_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_open_pr=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")

    def test_legacy_active_checkpoint_with_active_ci_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_active_ci=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")

    def test_terminal_result_supersedes_legacy_active_checkpoint(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_live_branch=True, has_terminal_result=True
        )
        self.assertEqual(state["state"], "STALE_LEGACY_CHECKPOINT")
        self.assertFalse(state["actionable"])

    def test_non_active_legacy_checkpoint_is_historical_terminal_state(self):
        state = reconcile_legacy_checkpoint_liveness(legacy_checkpoint("COMPLETE"))
        self.assertEqual(state["state"], "LEGACY_CHECKPOINT_TERMINAL")
        self.assertFalse(state["actionable"])

    def test_ci_dispatch_is_required_when_no_exact_run_exists(self):
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", []
        )
        self.assertEqual(decision["decision"], "DISPATCH_REQUIRED")

    def test_ci_dispatch_reuses_exact_active_run(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "in_progress",
            "conclusion": None,
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_ACTIVE_RUN")
        self.assertEqual(decision["run_id"], 101)

    def test_ci_dispatch_reuses_exact_successful_run(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_SUCCESSFUL_RUN")

    def test_ci_dispatch_routes_exact_failure_to_recovery(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "ROUTE_RECOVERY")

    def test_ci_dispatch_uses_latest_exact_context_run(self):
        runs = [
            {
                "id": 101,
                "name": "Project CI",
                "head_sha": "a" * 40,
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-03T01:00:00Z",
            },
            {
                "id": 102,
                "name": "Project CI",
                "head_sha": "a" * 40,
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-10-03T01:01:00Z",
            },
        ]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_SUCCESSFUL_RUN")
        self.assertEqual(decision["run_id"], 102)

    def test_ci_dispatch_does_not_reuse_different_event_context(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "DISPATCH_REQUIRED")

    def test_recent_in_progress_ci_is_wait_not_failure(self):
        run = {"status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:25:12Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "WAITING_EXTERNAL_CI")

    def test_old_in_progress_ci_requires_investigation_not_retry(self):
        run = {"status": "in_progress", "conclusion": None, "updated_at": "2026-10-02T22:00:00Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "INVESTIGATE_STALE_CI")

    def test_completed_success_is_terminal_success(self):
        self.assertEqual(classify_external_ci({"status": "completed", "conclusion": "success"}), "COMPLETED_SUCCESS")


    def test_external_ci_wait_remains_wait_only_while_bound_run_is_active(self):
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        runs = [{"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:30:00Z"}]
        state = reconcile_external_ci_wait([101], runs, now=now)
        self.assertEqual(state["state"], "WAITING_EXTERNAL_CI")
        self.assertEqual(state["route"], "WAIT")

    def test_terminal_success_invalidates_previous_wait_and_routes_continue(self):
        runs = [{"id": 101, "status": "completed", "conclusion": "success"}]
        state = reconcile_external_ci_wait([101], runs, previous_state="WAITING_EXTERNAL_CI")
        self.assertEqual(state["state"], "STALE_WAIT_STATE")
        self.assertEqual(state["route"], "AUDIT_CONTINUE")
        self.assertEqual(state["failed_run_ids"], [])

    def test_terminal_failure_invalidates_previous_wait_and_routes_recovery(self):
        runs = [{"id": 101, "status": "completed", "conclusion": "failure"}]
        state = reconcile_external_ci_wait([101], runs, previous_state="WAITING_EXTERNAL_CI")
        self.assertEqual(state["state"], "STALE_WAIT_STATE")
        self.assertEqual(state["route"], "RECOVERY")
        self.assertEqual(state["failed_run_ids"], [101])

    def test_mixed_active_and_terminal_runs_do_not_redispatch_early(self):
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        runs = [
            {"id": 101, "status": "completed", "conclusion": "success"},
            {"id": 102, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:30:00Z"},
        ]
        state = reconcile_external_ci_wait([101, 102], runs, now=now)
        self.assertEqual(state["state"], "WAITING_EXTERNAL_CI")
        self.assertEqual(state["route"], "WAIT")
        self.assertEqual(state["active_run_ids"], [102])

    def test_missing_bound_run_requires_investigation_not_new_dispatch(self):
        state = reconcile_external_ci_wait([101, 102], [{"id": 101, "status": "completed", "conclusion": "success"}])
        self.assertEqual(state["state"], "INVESTIGATE_CI_STATE")
        self.assertEqual(state["route"], "INVESTIGATE")
        self.assertEqual(state["missing_run_ids"], [102])

    def test_duplicate_wait_run_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_external_ci_wait([101, 101], [])


if __name__ == "__main__":
    unittest.main()

import copy
import json
import unittest
from pathlib import Path

from control.validate_records import (
    validate_checkpoint,
    validate_pair,
    validate_result,
    validate_scope,
    validate_task,
    validate_transition_authorization,
    validate_transition_pair,
    validate_transition_result,
)

ROOT = Path(__file__).resolve().parents[1]

def valid_task():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "project": "TEST",
        "repository": "owner/repo",
        "created_at": "2026-10-02T21:30:00Z",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "Test bounded control task",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/test-control-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["control/**"],
        "allowed_actions": ["create_branch", "create_commit"],
        "prohibited_actions": ["merge_to_main"],
        "human_gates": [{"action": "merge_to_main", "requires_owner_approval": True}],
        "required_validation": ["unit"],
        "required_ci": ["CI"],
        "terminal_condition": "PR green; no merge.",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }

def valid_result():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "terminal_status": "TERMINAL_SUCCESS",
        "repository": "owner/repo",
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "authorization_record": ".project-leader/tasks/TEST-CONTROL-001.json",
        "implementation_head_sha": "b" * 40,
        "branch": "builder/test-control-001",
        "pr_number": 1,
        "recorded_at": "2026-10-02T21:40:00Z",
        "state_observed_at": "2026-10-02T21:39:00Z",
        "superseded_by": None,
        "post_transition_record": None,
        "changes": ["example"],
        "validation": [{"name": "unit", "status": "PASS", "evidence": "local"}],
        "ci": [{"name": "CI", "status": "SUCCESS", "run_id": 1}],
        "artifacts": [],
        "material_non_effects": ["no merge"],
        "residual_blockers": [],
    }

def valid_v2_task():
    record = valid_task()
    record["schema_version"] = "2.0"
    record["integrity_mode"] = "IMMUTABLE_AUTHORIZATION_V1"
    record["recovery"] = {"mode": "APPEND_ONLY_V1"}
    record["policy"] = {
        "binding_mode": "LOCAL_BASE_V1",
        "profile": "project-leader-v1",
        "path": "projects/policies/project-leader.json",
        "base_sha": record["starting_state"]["base_sha"],
        "sha256": "d" * 64,
    }
    return record


def valid_v2_result():
    record = valid_result()
    record["schema_version"] = "2.0"
    record["authorization_commit_sha"] = "c" * 40
    record["authorization_sha256"] = "e" * 64
    return record


def valid_checkpoint():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "updated_at": "2026-10-02T21:41:00Z",
        "last_durable_step": "task authorization persisted",
        "action_fingerprint": "TEST-CONTROL-001|owner/repo|ci|run",
        "attempt_count": 1,
        "identical_failure_count": 0,
        "no_progress_iterations": 0,
        "strategy": "run required checks",
        "strategy_generation": 1,
        "last_error": None,
        "next_step": "audit CI",
        "status": "ACTIVE",
    }

def valid_transition_authorization():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-CONTROL-001-MERGE",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "created_at": "2026-10-02T21:50:00Z",
        "action": "merge_to_main",
        "effect_class": "E2_CONSEQUENTIAL_TRANSITION",
        "authority": {
            "source": "CURRENT_OWNER_INSTRUCTION",
            "summary": "Owner authorizes merge of the exact reviewed PR head.",
            "binding_mode": "EXACT_REVISION_BOUND",
        },
        "target": {
            "kind": "pull_request",
            "identifier": "#1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
    }

def valid_transition_result():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-CONTROL-001-MERGE",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "terminal_status": "SUCCESS",
        "authorization_record": ".project-leader/transitions/TEST-CONTROL-001-MERGE.authorization.json",
        "action": "merge_to_main",
        "target": {
            "kind": "pull_request",
            "identifier": "#1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
        "observed_at": "2026-10-02T21:55:00Z",
        "final_state": {"status": "MERGED", "revision": "c" * 40},
        "evidence": ["PR #1 merged", "main=c"],
        "residual_blockers": [],
    }

class ControlContractTests(unittest.TestCase):
    def assertInvalidTask(self, mutate):
        record = valid_task()
        mutate(record)
        with self.assertRaises(ValueError):
            validate_task(record)

    def assertInvalidResult(self, mutate):
        record = valid_result()
        mutate(record)
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_schemas_are_valid_json_and_require_core_fields(self):
        task = json.loads((ROOT / "control/task-authorization.schema.json").read_text())
        result = json.loads((ROOT / "control/worker-result.schema.json").read_text())
        checkpoint = json.loads((ROOT / "control/recovery-checkpoint.schema.json").read_text())
        transition_auth = json.loads((ROOT / "control/transition-authorization.schema.json").read_text())
        transition_result = json.loads((ROOT / "control/transition-result.schema.json").read_text())
        self.assertIn("task_id", task["required"])
        self.assertIn("human_gates", task["required"])
        self.assertIn("implementation_head_sha", result["required"])
        self.assertIn("material_non_effects", result["required"])
        self.assertIn("attempt_count", checkpoint["required"])
        self.assertIn("authority", transition_auth["required"])
        self.assertIn("authorization_record", transition_result["required"])

    def test_plugins_use_same_required_github_connector(self):
        pl = json.loads((ROOT / "plugins/project-leader/.app.json").read_text())
        rg = json.loads((ROOT / "plugins/recovery-guardian/.app.json").read_text())
        self.assertTrue(pl["apps"]["github"]["required"])
        self.assertEqual(pl["apps"]["github"]["id"], rg["apps"]["github"]["id"])

    def test_historical_records_remain_valid(self):
        task = json.loads((ROOT / ".project-leader/tasks/PROJECT-LEADER-CONTROL-HARDENING-003.json").read_text())
        result = json.loads((ROOT / ".project-leader/results/PROJECT-LEADER-CONTROL-HARDENING-003.json").read_text())
        self.assertTrue(validate_task(task))
        self.assertTrue(validate_result(result))

    def test_valid_pair(self):
        self.assertTrue(validate_pair(valid_task(), valid_result()))

    def test_unknown_field_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("unexpected", True))

    def test_invalid_authority_kind_fails(self):
        self.assertInvalidTask(lambda r: r["authority"].__setitem__("kind", "MAGIC"))

    def test_invalid_date_time_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("created_at", "yesterday"))

    def test_duplicate_array_item_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("mutation_scope", ["control/**", "control/**"]))

    def test_malformed_repository_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("repository", "owner/repo/extra"))

    def test_nested_unknown_field_fails(self):
        self.assertInvalidTask(lambda r: r["authority"].__setitem__("extra", "nope"))

    def test_human_gate_false_fails(self):
        self.assertInvalidTask(lambda r: r["human_gates"][0].__setitem__("requires_owner_approval", False))

    def test_result_invalid_sha_fails(self):
        self.assertInvalidResult(lambda r: r.__setitem__("implementation_head_sha", "abc"))

    def test_result_unknown_validation_field_fails(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("extra", "nope"))

    def test_terminal_success_with_failed_validation_fails(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("status", "FAIL"))

    def test_terminal_success_with_pending_ci_fails(self):
        self.assertInvalidResult(lambda r: r["ci"][0].__setitem__("status", "PENDING"))

    def test_terminal_success_requires_nonempty_validation(self):
        self.assertInvalidResult(lambda r: r.__setitem__("validation", []))

    def test_terminal_success_requires_positive_pass(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("status", "SKIPPED"))

    def test_skipped_validation_requires_justification(self):
        record = valid_result()
        record["validation"].append({"name": "optional", "status": "SKIPPED"})
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_duplicate_validation_name_fails(self):
        record = valid_result()
        record["validation"].append(copy.deepcopy(record["validation"][0]))
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_pair_task_id_mismatch_fails(self):
        result = valid_result()
        result["task_id"] = "OTHER-TASK-001"
        result["authorization_record"] = ".project-leader/tasks/OTHER-TASK-001.json"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_repository_mismatch_fails(self):
        result = valid_result()
        result["repository"] = "owner/other"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_branch_mismatch_fails(self):
        result = valid_result()
        result["branch"] = "builder/other"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_authorization_path_mismatch_fails(self):
        result = valid_result()
        result["authorization_record"] = ".project-leader/tasks/wrong.json"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_pr_mismatch_fails_when_task_binds_pr(self):
        task = valid_task()
        task["starting_state"]["pr_number"] = 99
        with self.assertRaises(ValueError):
            validate_pair(task, valid_result())

    def test_required_validation_cannot_be_skipped(self):
        result = valid_result()
        result["validation"][0]["status"] = "SKIPPED"
        result["validation"].append({"name": "other", "status": "PASS", "evidence": "ok"})
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_required_ci_must_exist(self):
        result = valid_result()
        del result["ci"]
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_required_ci_must_be_success(self):
        result = valid_result()
        result["ci"][0]["status"] = "NOT_APPLICABLE"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_scope_validation_accepts_authorized_paths(self):
        self.assertTrue(validate_scope(valid_task(), ["control/validate_records.py", "control/x/y.json"]))

    def test_scope_validation_rejects_outside_paths(self):
        with self.assertRaises(ValueError):
            validate_scope(valid_task(), ["control/validate_records.py", "README.md"])

    def test_checkpoint_limits_are_enforced(self):
        checkpoint = valid_checkpoint()
        self.assertTrue(validate_checkpoint(checkpoint))
        checkpoint["attempt_count"] = 4
        with self.assertRaises(ValueError):
            validate_checkpoint(checkpoint)

    def test_transition_pair_is_exact_revision_bound(self):
        self.assertTrue(validate_transition_pair(valid_transition_authorization(), valid_transition_result()))

    def test_successful_transition_requires_authorization_record(self):
        result = valid_transition_result()
        result["authorization_record"] = None
        with self.assertRaises(ValueError):
            validate_transition_result(result)

    def test_historical_transition_gap_is_recordable_without_fake_authorization(self):
        result = valid_transition_result()
        result["terminal_status"] = "HISTORICAL_OBSERVED"
        result["authorization_record"] = None
        result["residual_blockers"] = ["No durable Owner authorization record exists in the repository."]
        self.assertTrue(validate_transition_result(result))

    def test_transition_authorization_binding_mode_is_exact(self):
        auth = valid_transition_authorization()
        auth["authority"]["binding_mode"] = "OBJECTIVE_SCOPE_BOUND"
        with self.assertRaises(ValueError):
            validate_transition_authorization(auth)

    def test_contracts_reference_durable_authorization(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text()
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text()
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text()
        control = (ROOT / "control/README.md").read_text()
        self.assertIn(".project-leader/tasks/<task-id>.json", project)
        self.assertIn("Task Authorization Record", skill)
        self.assertIn(".project-leader/checkpoints/<task-id>.json", recovery)
        self.assertIn("Human-Gate Transition", control)


    def test_v2_central_policy_revision_can_differ_from_target_base(self):
        task = valid_v2_task()
        task["policy"] = {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "managed-v1",
            "path": "projects/policies/managed.json",
            "repository": "owner/control",
            "revision": "c" * 40,
            "sha256": "d" * 64,
        }
        self.assertNotEqual(task["starting_state"]["base_sha"], task["policy"]["revision"])
        self.assertTrue(validate_task(task))

    def test_v2_central_policy_requires_repository_and_revision(self):
        task = valid_v2_task()
        task["policy"] = {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "managed-v1",
            "path": "projects/policies/managed.json",
            "repository": "owner/control",
            "sha256": "d" * 64,
        }
        with self.assertRaises(ValueError):
            validate_task(task)

    def test_blocked_v2_result_can_truthfully_have_no_changes_or_ci(self):
        result = valid_v2_result()
        result["terminal_status"] = "BLOCKED"
        result["changes"] = []
        result["validation"] = []
        result["ci"] = []
        result["residual_blockers"] = ["Central policy binding is unavailable."]
        self.assertTrue(validate_result(result))

    def test_blocked_v2_result_requires_a_residual_blocker(self):
        result = valid_v2_result()
        result["terminal_status"] = "BLOCKED"
        result["changes"] = []
        result["validation"] = []
        result["ci"] = []
        result["residual_blockers"] = []
        with self.assertRaises(ValueError):
            validate_result(result)

    def test_immutable_v2_pair_requires_authorization_digest_and_commit(self):
        task = valid_v2_task()
        result = valid_v2_result()
        del result["authorization_sha256"]
        with self.assertRaises(ValueError):
            validate_pair(task, result)



    def test_skill_distinguishes_development_branch_merge_from_main_gate(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("inspect the live PR base branch", skill)
        self.assertIn("Only a PR whose base branch is exactly `main` is a merge-to-main transition.", skill)
        self.assertIn("If the PR base is not `main`, do not classify the merge itself as `merge_to_main`", skill)
        self.assertIn("merge_development_branch", skill)
        self.assertIn("continue automatically", skill)

    def test_project_leader_converges_before_human_gate(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("DETECT -> AUDIT -> CORRECT -> VALIDATE -> CONTINUE", skill)
        self.assertIn("convergence preflight", skill)
        self.assertIn("The mere existence of a gated PR", skill)
        self.assertIn("no covered corrective/preparatory work remains", skill)
        self.assertIn("An audit finding is an input to remediation", project)
        self.assertIn("Do not stop merely to report a covered problem", runbook)

    def test_project_leader_recovers_stale_external_ci_wait(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("STALE_WAIT_STATE", project)
        self.assertIn("STALE_WAIT_STATE", runbook)
        self.assertIn("STALE_WAIT_STATE", recovery)
        self.assertIn("STALE_WAIT_STATE", skill)
        self.assertIn("STALE_WAIT_STATE", guardian)
        self.assertIn("exact live run IDs", project)
        self.assertIn("all-success routes immediately to Supervisor audit/validate/continue", recovery)
        self.assertIn("chat/UI spinner", recovery)

    def test_project_leader_requires_durable_v2_recovery_events_before_retry(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        self.assertIn("FAILURE_OBSERVED", skill)
        self.assertIn("RETRY_AUTHORIZED", skill)
        self.assertIn("RECOVERED", skill)
        self.assertIn("run_attempt > 1", recovery)
        self.assertIn("Terminal certification must fail", recovery)
        self.assertIn("retroactive event is invalid", recovery)

    def test_legacy_active_checkpoint_requires_live_corroboration(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("STALE_LEGACY_CHECKPOINT", project)
        self.assertIn("STALE_LEGACY_CHECKPOINT", recovery)
        self.assertIn("STALE_LEGACY_CHECKPOINT", skill)
        self.assertIn("STALE_LEGACY_CHECKPOINT", guardian)
        self.assertIn("live branch", recovery)
        self.assertIn("open PR", recovery)

    def test_repository_hygiene_is_bounded_to_safe_branch_cleanup(self):
        workflow = (ROOT / ".github/workflows/repository-hygiene.yml").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("github.event.pull_request.head.ref != 'main'", workflow)
        self.assertIn("if (branch.name === 'main') continue;", workflow)
        self.assertIn("merge_base_commit", workflow)
        self.assertIn("mergeBase === branch.commit.sha", workflow)
        self.assertIn("github.rest.git.deleteRef", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch' ||", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("state: 'open'", workflow)
        self.assertIn("openPrHeads.has(branch.name)", workflow)
        self.assertIn("branchState.sha !== mainState.sha", workflow)
        self.assertIn("['added', 'modified', 'removed']", workflow)
        self.assertIn("files.length >= 300", workflow)
        self.assertIn("byte-identical to canonical `main`", runbook)
        self.assertIn("no open pull request", runbook)
        self.assertIn("never target `main`", runbook)

    def test_runtime_contract_documents_are_consistent_for_v2_managed_projects(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        builder = (ROOT / "AGENT_BUILDER_PROMPT.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        self.assertIn("CENTRAL_CONTROL_V1", project)
        self.assertIn("CENTRAL_CONTROL_V1", runbook)
        self.assertIn("CENTRAL_CONTROL_V1", builder)
        self.assertIn("CENTRAL_CONTROL_V1", skill)
        self.assertIn("IMMUTABLE_AUTHORIZATION_V1", project)
        self.assertIn("IMMUTABLE_AUTHORIZATION_V1", builder)
        self.assertIn("WAITING_EXTERNAL_CI", recovery)
        self.assertNotIn("whose central profile declares a control contract", builder)

if __name__ == "__main__":
    unittest.main()

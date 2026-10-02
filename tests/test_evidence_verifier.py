import unittest

from control.verify_github_evidence import verify_compare_payload, verify_run_payload


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


if __name__ == "__main__":
    unittest.main()

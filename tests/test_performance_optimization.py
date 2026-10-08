"""Meaningful measurement-math/guard tests for the offline performance harness."""

import math
import unittest

from scripts.performance_optimization import BASE, PORT, WORKLOADS, summary


class PerformanceHarnessTests(unittest.TestCase):
    def test_nearest_rank_p95_and_separate_median(self):
        result = summary(list(range(1, 21)))
        self.assertEqual(result["count"], 20)
        self.assertEqual(result["p50"], 10.5)
        self.assertEqual(result["p95"], 19)
        self.assertAlmostEqual(result["stddev"], math.sqrt(35))
        self.assertNotIn("p99", result)

    def test_invalid_samples_fail_closed(self):
        for values in ([], [-1], [float("nan")], [float("inf")]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                summary(values)

    def test_single_sample_has_no_invented_variance(self):
        self.assertEqual(summary([2])["stddev"], 0)

    def test_control_group_has_explicit_lanes_and_required_workloads(self):
        self.assertEqual(len(WORKLOADS), 10)
        self.assertIn("mongo_onboarding", WORKLOADS)
        self.assertIn("uncertain_policy_recovery", WORKLOADS)
        self.assertIn("native_document", WORKLOADS)
        self.assertEqual(len(BASE), 40)
        self.assertNotEqual(PORT, 27017)


if __name__ == "__main__":
    unittest.main()

"""Adverse regressions for PR79 measurement synchronization."""

import threading
import unittest
from unittest.mock import patch

from scripts.performance_concurrency import ActiveProviderProbe
from scripts.performance_optimization import Resources


class ResourceReadinessTests(unittest.TestCase):
    def test_first_sample_precedes_enter_and_fast_sections_never_empty(self):
        for _ in range(200):
            with Resources() as resources:
                self.assertTrue(resources.first_sample.is_set())
                self.assertGreater(resources.peak_rss, 0)
                self.assertTrue(resources.host_cpu)
            self.assertFalse(resources.thread.is_alive())

    def test_readiness_timeout_stops_and_joins(self):
        resources = Resources(startup_seconds=0.02, join_seconds=1)
        with patch.object(resources, "poll", side_effect=lambda: resources.stop.wait(1)):
            resources.thread = threading.Thread(target=resources.poll, daemon=True)
            with self.assertRaisesRegex(RuntimeError, "first observation"):
                resources.__enter__()
        self.assertTrue(resources.stop.is_set())
        self.assertFalse(resources.thread.is_alive())

    def test_invalid_observation_fails_closed(self):
        with patch("psutil.cpu_percent", return_value=float("nan")):
            resources = Resources(startup_seconds=0.03)
            with self.assertRaisesRegex(RuntimeError, "first observation"):
                resources.__enter__()
        self.assertFalse(resources.thread.is_alive())
        self.assertFalse(resources.host_cpu)

    def test_unexpected_sampler_errors_are_contained_without_false_evidence(self):
        for error in (RuntimeError, ValueError, TypeError, OSError):
            with self.subTest(error=error.__name__):
                resources = Resources(startup_seconds=0.03, join_seconds=1)
                with (
                    patch("psutil.Process", side_effect=error("synthetic OS detail")),
                    patch("threading.excepthook") as unhandled,
                    self.assertRaisesRegex(RuntimeError, "first observation"),
                ):
                    resources.__enter__()
                unhandled.assert_not_called()
                self.assertFalse(resources.first_sample.is_set())
                self.assertFalse(resources.thread.is_alive())
                self.assertEqual(resources.peak_rss, 0)
                self.assertEqual(resources.host_cpu, [])

    def test_join_failure_is_bounded_and_reported(self):
        resources = Resources(join_seconds=0.01)
        with patch.object(resources.thread, "join") as join, patch.object(
            resources.thread, "is_alive", return_value=True
        ), self.assertRaisesRegex(RuntimeError, "did not stop"):
            resources.__exit__()
        join.assert_called_once_with(0.01)


class ActiveProbeTests(unittest.TestCase):
    def test_dispatch_cannot_begin_without_held_active_provider(self):
        with (
            ActiveProviderProbe(hold_seconds=0.02) as probe,
            self.assertRaisesRegex(RuntimeError, "held active"),
        ):
            probe.begin_dispatch()

    def test_provider_is_held_through_dispatch_then_completion_releases(self):
        with ActiveProviderProbe(hold_seconds=1) as probe:
            worker = threading.Thread(target=lambda: probe.observe(lambda: 42))
            worker.start()
            self.assertTrue(probe.entered.wait(1))
            probe.begin_dispatch()
            self.assertGreater(probe.active_at_dispatch, 0)
            self.assertFalse(probe.release.is_set())
            probe.complete_health()
            worker.join(1)
            self.assertFalse(worker.is_alive())
        self.assertEqual(probe.active, 0)
        self.assertTrue(probe.completed_while_held)
        self.assertEqual(probe.release_reason, "health_completed")

    def test_blocked_health_uses_independent_release(self):
        with ActiveProviderProbe(hold_seconds=0.02) as probe:
            worker = threading.Thread(target=lambda: probe.observe(lambda: 42))
            worker.start()
            self.assertTrue(probe.entered.wait(1))
            probe.begin_dispatch()
            self.assertTrue(probe.release.wait(1))
            worker.join(1)
            probe.complete_health()
        self.assertEqual(probe.active, 0)
        self.assertFalse(probe.completed_while_held)
        self.assertEqual(probe.release_reason, "diagnostic_deadline")

    def test_exception_in_measuring_thread_releases_provider_and_joins_guard(self):
        probe = ActiveProviderProbe(hold_seconds=1)
        with self.assertRaisesRegex(ValueError, "measurement failure"), probe:
            worker = threading.Thread(target=lambda: probe.observe(lambda: 42))
            worker.start()
            self.assertTrue(probe.entered.wait(1))
            raise ValueError("measurement failure")
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertFalse(probe.guard.is_alive())
        self.assertEqual(probe.active, 0)

    def test_stale_entered_signal_after_release_cannot_dispatch_health(self):
        with ActiveProviderProbe(hold_seconds=0.01) as probe:
            worker = threading.Thread(target=lambda: probe.observe(lambda: 42))
            worker.start()
            self.assertTrue(probe.entered.wait(1))
            probe.begin_dispatch()
            self.assertTrue(probe.release.wait(1))
            worker.join(1)
            with self.assertRaisesRegex(RuntimeError, "held active"):
                probe.begin_dispatch()
        self.assertEqual(probe.active, 0)

    def test_provider_exception_balances_active_count(self):
        with ActiveProviderProbe() as probe:
            with self.assertRaisesRegex(ValueError, "provider failure"):
                probe.observe(lambda: (_ for _ in ()).throw(ValueError("provider failure")))
            self.assertEqual(probe.active, 0)
            self.assertFalse(probe.entered.is_set())

    def test_expired_provider_hold_fails_closed(self):
        probe = ActiveProviderProbe(operation_seconds=0.02)
        with self.assertRaisesRegex(RuntimeError, "provider hold"):
            probe.observe(lambda: 42)
        self.assertEqual(probe.active, 0)

    def test_primary_cohort_bytes_except_unused_binding_are_unchanged(self):
        import inspect
        import subprocess

        from scripts.performance_concurrency import measure_level
        from scripts.performance_optimization import ROOT

        old = subprocess.check_output(
            ["git", "show",
             "b4ee8e92025eefc5946216befb417af15e6de356:scripts/performance_concurrency.py"],
            cwd=ROOT,
            text=True,
        )
        old_function = old[old.index("def measure_level("):old.index("\ndef run(")].rstrip()
        # R3 authorizes only this unused tuple-binding rename. Keep the exact
        # cohort-body barrier for every other byte, including all assertions.
        source = inspect.getsource(measure_level).rstrip()
        before = "as (client, bundle, target, registry)"
        after = "as (client, _bundle, target, registry)"
        self.assertEqual(old_function.count(before), 1)
        self.assertEqual(source.count(after), 1)
        self.assertEqual(source.replace(after, before), old_function)

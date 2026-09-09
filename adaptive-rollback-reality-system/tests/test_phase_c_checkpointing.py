"""
Phase C Adaptive Checkpointing and Rollback Efficiency Test Suite.
Validates:
1. Normal checkpoint interval (~10s logical spacing, ~5 samples at 2s)
2. Warning checkpoint interval (~5s logical spacing, ~2-3 samples at 2s)
3. Critical checkpoint interval (1s logical maximum, saving every available sample)
4. Status escalation immediate checkpointing
5. Dataset timestamp timeline vs wall-clock independence
6. Storage reduction percentage and compression ratio calculations
7. Terminal failure incident checkpoint preservation
8. Backward compatibility fallback without timestamps
9. Deterministic experiment verification across MACHINE_001
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Isolate database writes to memory during tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.config import settings
from backend.checkpoint_controller import CheckpointController
from backend.dataset_loader import DatasetLoader
from backend.physical_state_vector import PhysicalStateVector
from backend.anomaly_detection import detector
from backend.failure_detector import failure_detector
from backend.ring_buffer import ring_buffer


class TestPhaseCCheckpointing(unittest.TestCase):

    def setUp(self):
        self.controller = CheckpointController()

    def tearDown(self):
        self.controller.reset()

    def test_01_normal_checkpoint_interval(self):
        """Verify NORMAL status checkpoints approximately every 10s of dataset time (5 samples)."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)
        saved_indices = []

        for i in range(25):  # 25 samples * 2s = 50 seconds
            ts = (base_time + timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S")
            _, should_save = self.controller.evaluate("NORMAL", timestamp=ts)
            if should_save:
                saved_indices.append(i)

        # First sample (i=0, t=0s), then i=5 (10s), i=10 (20s), i=15 (30s), i=20 (40s)
        self.assertEqual(saved_indices, [0, 5, 10, 15, 20])
        metrics = self.controller.get_metrics()
        self.assertEqual(metrics["total_states_received"], 25)
        self.assertEqual(metrics["total_checkpoints"], 5)
        self.assertEqual(metrics["effective_intervals"]["NORMAL"], 10.0)

    def test_02_warning_checkpoint_interval(self):
        """Verify WARNING status checkpoints approximately every 5s of dataset time (2-3 samples)."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)
        saved_indices = []

        for i in range(15):  # 15 samples * 2s = 30 seconds
            ts = (base_time + timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S")
            _, should_save = self.controller.evaluate("WARNING", timestamp=ts)
            if should_save:
                saved_indices.append(i)

        # i=0 (0s), i=3 (6s >= 5s), i=6 (12s >= 5s), i=9 (18s >= 5s), i=12 (24s >= 5s)
        self.assertEqual(saved_indices, [0, 3, 6, 9, 12])
        metrics = self.controller.get_metrics()
        self.assertEqual(metrics["total_checkpoints"], 5)
        self.assertEqual(metrics["effective_intervals"]["WARNING"], 6.0)

    def test_03_critical_checkpoint_interval(self):
        """Verify CRITICAL status uses 1s logical maximum, checkpointing every available 2s sample."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)
        saved_indices = []

        for i in range(10):  # 10 samples * 2s = 20 seconds
            ts = (base_time + timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S")
            _, should_save = self.controller.evaluate("CRITICAL", timestamp=ts)
            if should_save:
                saved_indices.append(i)

        # Every single state must be saved (10 out of 10)
        self.assertEqual(saved_indices, list(range(10)))
        metrics = self.controller.get_metrics()
        self.assertEqual(metrics["total_states_received"], 10)
        self.assertEqual(metrics["total_checkpoints"], 10)
        self.assertEqual(metrics["effective_intervals"]["CRITICAL"], 2.0)

    def test_04_status_escalation_immediate_checkpoint(self):
        """Verify transitions to higher risk (NORMAL -> WARNING -> CRITICAL) trigger immediate checkpoint."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)

        # t=0s: NORMAL (first state -> saved)
        _, s0 = self.controller.evaluate("NORMAL", timestamp=(base_time).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertTrue(s0)

        # t=2s: NORMAL (2s < 10s -> not saved)
        _, s1 = self.controller.evaluate("NORMAL", timestamp=(base_time + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertFalse(s1)

        # t=4s: Status escalates to WARNING -> immediate checkpoint!
        _, s2 = self.controller.evaluate("WARNING", timestamp=(base_time + timedelta(seconds=4)).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertTrue(s2, "Status escalation from NORMAL to WARNING must trigger immediate checkpoint")

        # t=6s: WARNING (2s < 5s -> not saved)
        _, s3 = self.controller.evaluate("WARNING", timestamp=(base_time + timedelta(seconds=6)).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertFalse(s3)

        # t=8s: Status escalates to CRITICAL -> immediate checkpoint!
        _, s4 = self.controller.evaluate("CRITICAL", timestamp=(base_time + timedelta(seconds=8)).strftime("%Y-%m-%d %H:%M:%S"))
        self.assertTrue(s4, "Status escalation from WARNING to CRITICAL must trigger immediate checkpoint")

    def test_05_dataset_timeline_independence_from_wallclock(self):
        """Verify checkpoint timing relies strictly on dataset timestamps regardless of pacing."""
        # Consecutive states spaced 10 seconds in dataset time
        t0 = "2026-01-01 08:00:00"
        t1 = "2026-01-01 08:00:10"
        t2 = "2026-01-01 08:00:12"

        _, s0 = self.controller.evaluate("NORMAL", timestamp=t0)
        self.assertTrue(s0)

        _, s1 = self.controller.evaluate("NORMAL", timestamp=t1)
        self.assertTrue(s1, "10s elapsed dataset time must trigger checkpoint")

        _, s2 = self.controller.evaluate("NORMAL", timestamp=t2)
        self.assertFalse(s2, "2s elapsed dataset time must not trigger NORMAL checkpoint")

    def test_06_storage_reduction_and_metrics_calculation(self):
        """Verify mathematical definitions for storage reduction volume, percentage, and ratio."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)

        # Stream 100 NORMAL states (200 dataset seconds)
        for i in range(100):
            ts = (base_time + timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S")
            self.controller.evaluate("NORMAL", timestamp=ts)

        metrics = self.controller.get_metrics()
        self.assertEqual(metrics["total_states_received"], 100)
        # Sample 0, 5, 10, 15, ..., 95 = 20 checkpoints
        self.assertEqual(metrics["total_checkpoints"], 20)
        self.assertEqual(metrics["storage_saved"], 80)
        self.assertEqual(metrics["storage_reduction_percent"], 80.0)
        self.assertEqual(metrics["storage_reduction_ratio"], 5.0)
        self.assertEqual(metrics["checkpoints_by_status"]["NORMAL"], 20)

    def test_07_failure_incident_checkpoint_preservation(self):
        """Verify terminal physical failure state is preserved and metrics freeze cleanly."""
        base_time = datetime(2026, 1, 1, 8, 0, 0)
        self.controller.evaluate("NORMAL", timestamp=base_time.strftime("%Y-%m-%d %H:%M:%S"))

        # Advance to failure point
        fail_ts = (base_time + timedelta(seconds=14)).strftime("%Y-%m-%d %H:%M:%S")
        _, should_save = self.controller.evaluate("FAILURE", timestamp=fail_ts)
        self.assertTrue(should_save, "FAILURE status must trigger immediate checkpoint")

        self.controller.record_failure(fail_ts)
        metrics = self.controller.get_metrics()
        self.assertGreaterEqual(metrics["checkpoints_by_status"]["FAILURE"], 1)

    def test_08_backward_compatibility_fallback(self):
        """Verify evaluate(status) without timestamp operates via fallback modulo state counts."""
        # NORMAL freq = 10
        saved = [self.controller.evaluate("NORMAL")[1] for _ in range(25)]
        # True at step 10 and step 20
        self.assertEqual(saved.count(True), 2)
        self.assertTrue(saved[9])
        self.assertTrue(saved[19])

        # WARNING freq = 5
        self.controller.reset()
        saved_warn = [self.controller.evaluate("WARNING")[1] for _ in range(15)]
        self.assertEqual(saved_warn.count(True), 3)

        # CRITICAL freq = 1
        self.controller.reset()
        saved_crit = [self.controller.evaluate("CRITICAL")[1] for _ in range(5)]
        self.assertEqual(saved_crit.count(True), 5)

    def test_09_deterministic_experiment_machine001(self):
        """Execute deterministic verification of adaptive checkpointing across MACHINE_001 dataset."""
        loader = DatasetLoader("MACHINE_001")
        self.controller.reset()
        ring_buffer.reset()

        total_steps = 1800
        for _ in range(total_steps):
            raw = loader.get_next_state()
            psv = PhysicalStateVector(
                timestamp=raw["timestamp"],
                device_id=raw["machine_id"],
                air_temperature=raw["air_temperature"],
                process_temperature=raw["process_temperature"],
                humidity=raw["humidity"],
                vibration=raw["vibration"],
                rotational_speed=raw["rotational_speed"],
                torque=raw["torque"],
                current=raw["current"],
                tool_wear=raw["tool_wear"],
                is_failure=False
            )
            score, status = detector.calculate_anomaly_score(psv)
            is_fail, fail_details = failure_detector.evaluate(psv, score)
            if is_fail:
                status = "FAILURE"
                psv.machine_status = "FAILURE"
                psv.is_failure = True
                ring_buffer.lock(fail_details)

            _, should_save = self.controller.evaluate(status, timestamp=raw["timestamp"])
            if is_fail and not should_save:
                self.controller.record_failure(raw["timestamp"])

        metrics = self.controller.get_metrics()

        # Deterministic benchmarks for MACHINE_001
        self.assertEqual(metrics["total_states_received"], 1800)
        self.assertGreater(metrics["total_checkpoints"], 700)
        self.assertLess(metrics["total_checkpoints"], 800)
        self.assertGreater(metrics["storage_reduction_percent"], 55.0)
        self.assertGreater(metrics["storage_reduction_ratio"], 2.0)

        # Verify all status categories have recorded checkpoints
        self.assertGreater(metrics["checkpoints_by_status"]["NORMAL"], 180)
        self.assertGreater(metrics["checkpoints_by_status"]["WARNING"], 50)
        self.assertGreater(metrics["checkpoints_by_status"]["CRITICAL"], 350)
        self.assertGreaterEqual(metrics["checkpoints_by_status"]["FAILURE"], 1)

        # Verify effective intervals align with logical requirements
        self.assertAlmostEqual(metrics["effective_intervals"]["NORMAL"], 10.0, delta=1.5)
        self.assertAlmostEqual(metrics["effective_intervals"]["WARNING"], 5.5, delta=1.5)
        self.assertEqual(metrics["effective_intervals"]["CRITICAL"], 2.0)


if __name__ == "__main__":
    unittest.main()

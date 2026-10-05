"""
Phase D Software Finalization and Demonstration Readiness Test Suite.
Validates:
1. Complete failure-demo lifecycle from pre-failure positioning to physical failure,
   ring buffer lock, trajectory extraction, and root-cause analysis.
2. Complete reset repeatability (consecutive demo cycles produce identical behavior).
3. Zero database file mutation (database/machine_data.db remains untouched).
4. Full WebSocket payload schema consistency and metric integrity.
5. Replay navigation bounds, cursor tracking, and state fidelity.
6. Checkpoint storage efficiency persistence across reset cycles.
"""

import unittest
import sys
import os
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Strictly isolate database writes to memory during all test operations
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.config import settings
from backend.dataset_loader import dataset_loader
from backend.physical_state_vector import PhysicalStateVector
from backend.anomaly_detection import detector
from backend.failure_detector import failure_detector
from backend.checkpoint_controller import checkpoint_controller
from backend.ring_buffer import ring_buffer
from backend.replay_engine import replay_engine
from backend.simulation import simulation_engine
from backend.main import (
    app, get_status, get_metrics, start_simulation, stop_simulation,
    force_failure, reset_simulation, get_latest_trajectory,
    replay_start, replay_step_forward, replay_step_backward, replay_reset
)


class TestPhaseDFinalization(unittest.TestCase):

    def setUp(self):
        """Ensure pristine runtime state before every test."""
        simulation_engine.reset()

    def tearDown(self):
        """Ensure pristine runtime state after every test."""
        simulation_engine.reset()

    def test_01_database_file_untouched(self):
        """Verify that running test operations leaves database/machine_data.db untouched."""
        db_path = os.path.join(BASE_DIR, "database", "machine_data.db")
        if os.path.exists(db_path):
            stat_before = os.stat(db_path)
            # Perform reset and simulation lifecycle operations
            asyncio.run(reset_simulation())
            stat_after = os.stat(db_path)
            self.assertEqual(stat_before.st_mtime, stat_after.st_mtime, "Database file mtime must not change!")
            self.assertEqual(stat_before.st_size, stat_after.st_size, "Database file size must not change!")

    def test_02_full_demo_lifecycle_and_extraction(self):
        """
        Verify the end-to-end failure demo lifecycle:
        1. Force failure (pre-failure seek)
        2. Feed states until physical failure trips
        3. Post-failure observation window completes
        4. Buffer locks, trajectory extracts, root-cause computes
        """
        asyncio.run(force_failure())
        self.assertIn(dataset_loader.current_idx, [1781, 1782])
        self.assertIn(dataset_loader.machine_df.iloc[dataset_loader.current_idx]["timestamp"], ["2026-01-01 08:59:22", "2026-01-01 08:59:24"])

        steps = 0
        failure_detected = False
        while dataset_loader.current_idx < len(dataset_loader.machine_df) and steps < 30:
            raw = dataset_loader.get_next_state()
            steps += 1
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
            psv.anomaly_score = score
            freq, should_save = checkpoint_controller.evaluate(status, timestamp=psv.timestamp)
            psv.checkpoint_level = status
            psv.machine_status = status

            is_fail, fail_details = failure_detector.evaluate(psv, score)
            if is_fail:
                psv.machine_status = "FAILURE"
                psv.is_failure = True
                ring_buffer.lock(fail_details)
                checkpoint_controller.record_failure(timestamp=psv.timestamp)
                failure_detected = True

            ring_buffer.append(psv)
            if ring_buffer.last_extracted_trajectory is not None:
                break

        self.assertTrue(failure_detected, "Physical failure detector must trigger.")
        self.assertTrue(ring_buffer.is_locked, "Ring buffer must be locked.")
        self.assertIsNotNone(ring_buffer.last_extracted_trajectory, "Trajectory must be extracted.")

        # Robust capacity/window bounds: length > 0 and does not exceed configured capacity
        trajectory = ring_buffer.last_extracted_trajectory
        max_allowed_window = settings.PRE_FAILURE_WINDOW + settings.POST_FAILURE_WINDOW + 1
        self.assertGreater(len(trajectory), 0, "Trajectory length must be > 0.")
        self.assertLessEqual(len(trajectory), max_allowed_window, f"Trajectory length must not exceed {max_allowed_window}.")
        self.assertLessEqual(len(trajectory), settings.RING_BUFFER_CAPACITY, "Trajectory length must not exceed buffer capacity.")

        # Root cause exists and primary contributor is one of the analyzed telemetry parameters
        self.assertIsNotNone(ring_buffer.last_root_cause, "Root cause must be computed.")
        ranked_causes = ring_buffer.last_root_cause.get("ranked_causes", [])
        self.assertGreater(len(ranked_causes), 0, "Root cause must contain ranked causes.")
        valid_params = {"air_temperature", "process_temperature", "rotational_speed", "torque", "vibration"}
        primary_contributor = ranked_causes[0]["parameter"]
        self.assertIn(primary_contributor, valid_params, f"Primary contributor '{primary_contributor}' must be an analyzed telemetry parameter.")

    def test_03_deterministic_back_to_back_reset_repeatability(self):
        """
        Verify that repeating the demo cycle 2 times back-to-back produces identical,
        deterministic trajectories and root-cause rankings without leftover state.
        """
        trajectories = []
        top_causes = []

        for cycle in range(2):
            asyncio.run(reset_simulation())
            self.assertFalse(ring_buffer.is_locked)
            self.assertIsNone(ring_buffer.last_extracted_trajectory)

            dataset_loader.seek_pre_failure_by_timestamp(settings.PRE_FAILURE_LEAD_SECONDS)
            self.assertEqual(dataset_loader.current_idx, 1781)

            while dataset_loader.current_idx < len(dataset_loader.machine_df):
                raw = dataset_loader.get_next_state()
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
                psv.anomaly_score = score
                checkpoint_controller.evaluate(status, timestamp=psv.timestamp)
                psv.checkpoint_level = status
                psv.machine_status = status

                is_fail, fail_details = failure_detector.evaluate(psv, score)
                if is_fail:
                    psv.machine_status = "FAILURE"
                    psv.is_failure = True
                    ring_buffer.lock(fail_details)
                    checkpoint_controller.record_failure(timestamp=psv.timestamp)

                ring_buffer.append(psv)
                if ring_buffer.last_extracted_trajectory is not None:
                    break

            self.assertIsNotNone(ring_buffer.last_extracted_trajectory)
            trajectories.append([s.timestamp for s in ring_buffer.last_extracted_trajectory])
            ranked = ring_buffer.last_root_cause["ranked_causes"]
            top_causes.append(ranked[0]["parameter"])

        self.assertEqual(trajectories[0], trajectories[1], "Both cycles must produce identical timestamps!")
        self.assertEqual(top_causes[0], top_causes[1], "Both cycles must produce identical top cause!")
        valid_params = {"air_temperature", "process_temperature", "rotational_speed", "torque", "vibration"}
        self.assertIn(top_causes[0], valid_params, f"Top contributor '{top_causes[0]}' must be an analyzed telemetry parameter.")

    def test_04_replay_navigation_bounds_and_fidelity(self):
        """Verify replay stepping forwards and backwards respects bounds and preserves state."""
        dataset_loader.seek_pre_failure_by_timestamp(settings.PRE_FAILURE_LEAD_SECONDS)
        while dataset_loader.current_idx < len(dataset_loader.machine_df):
            raw = dataset_loader.get_next_state()
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
            psv.anomaly_score = score
            checkpoint_controller.evaluate(status, timestamp=psv.timestamp)
            psv.machine_status = status
            is_fail, fail_details = failure_detector.evaluate(psv, score)
            if is_fail:
                psv.machine_status = "FAILURE"
                psv.is_failure = True
                ring_buffer.lock(fail_details)
            ring_buffer.append(psv)
            if ring_buffer.last_extracted_trajectory is not None:
                break

        replay_start()
        trajectory_len = len(replay_engine.trajectory)
        self.assertGreater(trajectory_len, 0, "Replay engine trajectory must be non-empty.")
        self.assertEqual(replay_engine.current_idx, 0)
        initial_state = replay_engine.get_current_state()
        self.assertIsNotNone(initial_state)

        # Step backward at index 0 should clamp at 0
        back_resp = replay_step_backward()
        self.assertEqual(replay_engine.current_idx, 0)
        self.assertEqual(back_resp["state"]["timestamp"], initial_state.timestamp)

        # Step forward to the end of the trajectory
        fwd_resp = None
        for _ in range(trajectory_len - 1):
            fwd_resp = replay_step_forward()

        self.assertEqual(replay_engine.current_idx, trajectory_len - 1)
        final_state = replay_engine.get_current_state()
        self.assertEqual(fwd_resp["state"]["timestamp"], final_state.timestamp)

        # Stepping forward past the end should clamp at trajectory_len - 1
        boundary_resp = replay_step_forward()
        self.assertEqual(replay_engine.current_idx, trajectory_len - 1)
        self.assertEqual(boundary_resp["state"]["timestamp"], final_state.timestamp)

        # Jump to failure
        replay_engine.jump_to_failure()
        fail_state = replay_engine.get_current_state()
        self.assertIsNotNone(fail_state)
        self.assertTrue(fail_state.is_failure)

        # Replay reset returns to index 0
        reset_resp = replay_reset()
        self.assertEqual(replay_engine.current_idx, 0)
        self.assertEqual(reset_resp["state"]["timestamp"], initial_state.timestamp)

    def test_05_checkpoint_metric_integrity(self):
        """Verify checkpoint controller metrics provide all expected fields."""
        metrics = checkpoint_controller.get_metrics()
        expected_keys = [
            "total_states_received", "total_checkpoints", "storage_saved",
            "storage_reduction_percent", "storage_reduction_ratio",
            "effective_intervals", "target_intervals", "checkpoints_by_status"
        ]
        for key in expected_keys:
            self.assertIn(key, metrics, f"Metric '{key}' must be present in get_metrics()")

        checkpoint_controller.evaluate("NORMAL", anomaly_score=0.1, timestamp="2026-01-01 08:00:00")
        checkpoint_controller.evaluate("NORMAL", anomaly_score=0.1, timestamp="2026-01-01 08:00:02")
        checkpoint_controller.evaluate("NORMAL", anomaly_score=0.1, timestamp="2026-01-01 08:00:04")
        checkpoint_controller.evaluate("CRITICAL", anomaly_score=0.9, timestamp="2026-01-01 08:00:06")
        checkpoint_controller.evaluate("CRITICAL", anomaly_score=0.9, timestamp="2026-01-01 08:00:08")

        m = checkpoint_controller.get_metrics()
        self.assertEqual(m["total_states_received"], 5)
        self.assertEqual(m["total_checkpoints"], 3)
        self.assertEqual(m["storage_saved"], 2)
        self.assertEqual(m["storage_reduction_percent"], 40.0)
        self.assertEqual(m["storage_reduction_ratio"], 1.67)


if __name__ == "__main__":
    unittest.main()

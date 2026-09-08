"""
Phase B End-to-End Software Demo Integration Test Suite.
Validates the complete 10-step demo flow:
1. Start simulation API
2. Display chronological MACHINE_001 telemetry
3. Show anomaly status progression NORMAL -> WARNING -> CRITICAL
4. Trigger failure-demo endpoint
5. Demonstrate runtime physical failure detection
6. Show ring-buffer lock state
7. Show extracted trajectory after post-failure capture completes
8. Show root-cause analysis using root_cause.py
9. Replay controls step backward and forward through extracted trajectory
10. Reset and repeat demonstration cleanly
"""

import unittest
import sys
import os
import asyncio

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Isolate database writes to memory during tests to protect database/machine_data.db
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
    get_status, get_metrics, start_simulation, stop_simulation,
    force_failure, reset_simulation, get_latest_trajectory,
    replay_start, replay_step_forward, replay_step_backward, replay_reset
)


class TestPhaseBIntegration(unittest.TestCase):

    def setUp(self):
        """Clean runtime state before every test."""
        simulation_engine.reset()

    def tearDown(self):
        """Clean runtime state after every test."""
        simulation_engine.reset()

    def test_01_simulation_start_and_stop_lifecycle(self):
        """Requirement 1: Start and stop simulation controls."""
        status_before = get_status()
        self.assertFalse(status_before["simulation_running"])
        self.assertFalse(status_before["buffer_locked"])

        # Start simulation
        res_start = asyncio.run(start_simulation())
        self.assertEqual(res_start["status"], "started")
        status_running = get_status()
        self.assertTrue(status_running["simulation_running"])

        # Stop simulation
        res_stop = asyncio.run(stop_simulation())
        self.assertEqual(res_stop["status"], "stopped")
        status_stopped = get_status()
        self.assertFalse(status_stopped["simulation_running"])

    def test_02_chronological_machine001_telemetry(self):
        """Requirement 2: Telemetry represents MACHINE_001 in chronological sequence."""
        dataset_loader.reset()
        first_state = dataset_loader.get_next_state()
        self.assertEqual(first_state["machine_id"], "MACHINE_001")
        self.assertEqual(first_state["timestamp"], "2026-01-01 08:00:00")
        self.assertIn("air_temperature", first_state)
        self.assertIn("process_temperature", first_state)
        self.assertIn("vibration", first_state)
        self.assertIn("rotational_speed", first_state)

        second_state = dataset_loader.get_next_state()
        self.assertEqual(second_state["machine_id"], "MACHINE_001")
        self.assertGreater(second_state["timestamp"], first_state["timestamp"])

    def test_03_anomaly_status_progression(self):
        """Requirement 3: Anomaly status progression NORMAL -> WARNING -> CRITICAL."""
        # 1. Normal state
        psv_normal = PhysicalStateVector(
            timestamp="2026-01-01 08:00:00",
            device_id="SIM-ESP32",
            air_temperature=22.8,
            process_temperature=43.3,
            humidity=48.3,
            vibration=0.10,
            rotational_speed=1485.0,
            torque=41.1,
            current=12.1,
            tool_wear=0.0
        )
        score_normal, status_normal = detector.calculate_anomaly_score(psv_normal)
        self.assertEqual(status_normal, "NORMAL")
        self.assertLess(score_normal, settings.WARNING_THRESHOLD)

        freq_normal, should_save = checkpoint_controller.evaluate(status_normal)
        self.assertEqual(freq_normal, settings.NORMAL_CHECKPOINT_FREQ)

        # 2. Critical anomalous state
        psv_critical = PhysicalStateVector(
            timestamp="2026-01-01 09:04:20",
            device_id="SIM-ESP32",
            air_temperature=22.7,
            process_temperature=76.3,
            humidity=48.2,
            vibration=0.40,
            rotational_speed=1483.0,
            torque=41.0,
            current=12.7,
            tool_wear=6.26
        )
        score_crit, status_crit = detector.calculate_anomaly_score(psv_critical)
        self.assertEqual(status_crit, "CRITICAL")
        self.assertGreaterEqual(score_crit, settings.CRITICAL_THRESHOLD)

        freq_crit, _ = checkpoint_controller.evaluate(status_crit)
        self.assertEqual(freq_crit, settings.CRITICAL_CHECKPOINT_FREQ)

        # 3. Warning evaluation
        freq_warn, _ = checkpoint_controller.evaluate("WARNING")
        self.assertEqual(freq_warn, settings.WARNING_CHECKPOINT_FREQ)

    def test_04_failure_demo_positioning(self):
        """Requirement 4: Trigger failure demo endpoint and verify pre-failure positioning."""
        dataset_loader.reset()
        target_idx = dataset_loader.seek_pre_failure_by_timestamp(settings.PRE_FAILURE_LEAD_SECONDS)
        self.assertEqual(target_idx, 1781)
        self.assertEqual(dataset_loader.machine_df.iloc[target_idx]["timestamp"], "2026-01-01 08:59:22")

        res = asyncio.run(force_failure())
        self.assertIn("Failure demo positioned", res["status"])
        self.assertTrue(simulation_engine.is_running)
        # Position is at or right after pre-failure target sequence 1781 as playback begins
        self.assertIn(dataset_loader.current_idx, [1781, 1782])

    def test_05_runtime_physical_failure_detection(self):
        """Requirement 5: Demonstrate runtime physical failure detection at limit breach."""
        # Seek pre-failure
        dataset_loader.seek_pre_failure_by_timestamp(settings.PRE_FAILURE_LEAD_SECONDS)
        failure_encountered = False
        failure_timestamp = None
        failure_reason = ""

        for step in range(25):
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
            is_fail, fail_details = failure_detector.evaluate(psv, score)
            if is_fail:
                failure_encountered = True
                failure_timestamp = psv.timestamp
                failure_reason = fail_details.get("reason", "")
                break

        self.assertTrue(failure_encountered)
        self.assertEqual(failure_timestamp, "2026-01-01 08:59:52")
        self.assertIn("Vibration", failure_reason)

    def test_06_ring_buffer_locking(self):
        """Requirement 6: Show ring-buffer lock state."""
        self.assertFalse(ring_buffer.is_locked)
        fail_details = {"timestamp": "2026-01-01 08:59:52", "causes": ["Vibration safety limit exceeded: 0.3507 > 0.35"]}
        ring_buffer.lock(fail_details)
        self.assertTrue(ring_buffer.is_locked)
        self.assertEqual(ring_buffer.failure_event, fail_details)

        status = get_status()
        self.assertTrue(status["buffer_locked"])

    def test_07_post_failure_capture_and_trajectory_extraction(self):
        """Requirement 7: Trajectory extraction after post-failure capture completes."""
        dataset_loader.seek_pre_failure_by_timestamp(settings.PRE_FAILURE_LEAD_SECONDS)
        ring_buffer.reset()

        # Step through until trajectory is extracted
        for _ in range(30):
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
            is_fail, fail_details = failure_detector.evaluate(psv, score)
            if is_fail:
                psv.machine_status = "FAILURE"
                psv.is_failure = True
                ring_buffer.lock(fail_details)

            ring_buffer.append(psv)
            if ring_buffer.last_extracted_trajectory is not None:
                break

        self.assertIsNotNone(ring_buffer.last_extracted_trajectory)
        trajectory = ring_buffer.last_extracted_trajectory
        # Window size: PRE_FAILURE_WINDOW (10) + FAILURE (1) + POST_FAILURE_WINDOW (4-5) = 15-16
        self.assertGreaterEqual(len(trajectory), 15)
        failure_states = [s for s in trajectory if s.is_failure]
        self.assertEqual(len(failure_states), 1)
        self.assertEqual(failure_states[0].timestamp, "2026-01-01 08:59:52")

    def test_08_root_cause_analysis_endpoint(self):
        """Requirement 8: Show root-cause analysis using existing root_cause.py via API."""
        # Run failure simulation to populate ring buffer trajectory
        self.test_07_post_failure_capture_and_trajectory_extraction()

        trajectory_response = get_latest_trajectory()
        self.assertIn("trajectory", trajectory_response)
        self.assertIn("root_cause", trajectory_response)

        root_cause = trajectory_response["root_cause"]
        self.assertIsNotNone(root_cause)
        self.assertIn("ranked_causes", root_cause)
        self.assertIn("causal_graph", root_cause)

        # Ranked causes verification
        ranked = root_cause["ranked_causes"]
        self.assertGreater(len(ranked), 0)
        top_cause = ranked[0]
        self.assertIn("parameter", top_cause)
        self.assertIn("contribution_percent", top_cause)
        self.assertIsInstance(top_cause["contribution_percent"], (float, int))

        # Causal graph verification
        graph = root_cause["causal_graph"]
        self.assertIn("Machine failure", graph)

    def test_09_replay_engine_controls(self):
        """Requirement 9: Replay controls step backward and forward through trajectory."""
        self.test_07_post_failure_capture_and_trajectory_extraction()

        # Start replay
        res_start = replay_start()
        self.assertEqual(res_start["status"], "ready")

        # Initial state via reset
        res_reset = replay_reset()
        initial_state = res_reset["state"]
        self.assertIsNotNone(initial_state)
        first_timestamp = initial_state["timestamp"]

        # Step forward
        res_step1 = replay_step_forward()
        step1_state = res_step1["state"]
        self.assertIsNotNone(step1_state)
        self.assertNotEqual(step1_state["timestamp"], first_timestamp)

        # Step forward again
        res_step2 = replay_step_forward()
        step2_state = res_step2["state"]
        self.assertIsNotNone(step2_state)
        self.assertNotEqual(step2_state["timestamp"], step1_state["timestamp"])

        # Step backward
        res_back = replay_step_backward()
        back_state = res_back["state"]
        self.assertEqual(back_state["timestamp"], step1_state["timestamp"])

        # Reset replay
        res_reset2 = replay_reset()
        self.assertEqual(res_reset2["state"]["timestamp"], first_timestamp)

    def test_10_reset_and_repeat_demonstration(self):
        """Requirement 10: Reset and repeat demonstration cleanly."""
        # First execution cycle
        self.test_07_post_failure_capture_and_trajectory_extraction()
        self.assertTrue(ring_buffer.is_locked)
        self.assertIsNotNone(ring_buffer.last_extracted_trajectory)

        # Reset via API
        res_reset = asyncio.run(reset_simulation())
        self.assertEqual(res_reset["status"], "reset")

        status_after_reset = get_status()
        self.assertFalse(status_after_reset["buffer_locked"])
        self.assertFalse(status_after_reset["simulation_running"])
        self.assertFalse(status_after_reset["trajectory_ready"])
        self.assertEqual(dataset_loader.current_idx, 0)
        self.assertIsNone(ring_buffer.last_extracted_trajectory)

        # Repeat execution cycle
        asyncio.run(force_failure())
        self.assertIn(dataset_loader.current_idx, [1781, 1782])
        self.assertTrue(simulation_engine.is_running)


if __name__ == "__main__":
    unittest.main()

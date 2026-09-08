"""
Phase A Validation Test Suite for data/machine_timeseries.csv integration.
Covers:
1. Chronological dataset loading
2. MACHINE_001 selection
3. Timestamp preservation
4. Real telemetry values
5. Ground-truth separation
6. Timestamp-based pre-failure seeking
7. Reset behaviour
8. Anomaly detection
9. Runtime failure detection
10. Ring-buffer locking & trajectory extraction
11. Repeated failure-demo execution & clean runtime reset
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Isolate database writes to memory during tests to protect database/machine_data.db
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.config import settings
from backend.dataset_loader import DatasetLoader, dataset_loader
from backend.physical_state_vector import PhysicalStateVector
from backend.anomaly_detection import AnomalyDetector, detector
from backend.failure_detector import FailureDetector, failure_detector
from backend.checkpoint_controller import checkpoint_controller
from backend.ring_buffer import ring_buffer
from backend.replay_engine import replay_engine
from backend.simulation import simulation_engine


class TestPhaseAValidation(unittest.TestCase):

    def test_01_chronological_dataset_loading(self):
        """Verify dataset loads in strict chronological sequence."""
        loader = DatasetLoader("MACHINE_001")
        self.assertEqual(len(loader.machine_df), 2000)
        seq_ids = loader.machine_df["sequence_id"].tolist()
        self.assertEqual(seq_ids, sorted(seq_ids))
        self.assertEqual(seq_ids[0], 0)
        self.assertEqual(seq_ids[-1], 1999)

    def test_02_machine_001_selection(self):
        """Verify default machine selection and extensibility."""
        loader = DatasetLoader("MACHINE_001")
        self.assertEqual(loader.selected_machine, "MACHINE_001")
        self.assertTrue((loader.machine_df["machine_id"] == "MACHINE_001").all())

        # Switch machine test
        loader.select_machine("MACHINE_002")
        self.assertEqual(loader.selected_machine, "MACHINE_002")
        self.assertTrue((loader.machine_df["machine_id"] == "MACHINE_002").all())

    def test_03_timestamp_preservation(self):
        """Verify dataset timestamp string is preserved unmodified."""
        loader = DatasetLoader("MACHINE_001")
        loader.reset()
        state = loader.get_next_state()
        expected_ts = str(loader.machine_df.iloc[0]["timestamp"])
        self.assertEqual(state["timestamp"], expected_ts)
        self.assertEqual(state["timestamp"], "2026-01-01 08:00:00")

    def test_04_real_telemetry_values(self):
        """Verify telemetry values match CSV directly with no random noise."""
        loader = DatasetLoader("MACHINE_001")
        loader.reset()
        state = loader.get_next_state()
        row = loader.machine_df.iloc[0]

        self.assertEqual(state["air_temperature"], float(row["air_temperature"]))
        self.assertEqual(state["process_temperature"], float(row["process_temperature"]))
        self.assertEqual(state["humidity"], float(row["humidity"]))
        self.assertEqual(state["vibration"], float(row["vibration"]))
        self.assertEqual(state["rotational_speed"], float(row["rotational_speed"]))
        self.assertEqual(state["torque"], float(row["torque"]))
        self.assertEqual(state["tool_wear"], float(row["tool_wear"]))
        self.assertEqual(state["current"], float(row["current"]))

    def test_05_ground_truth_separation(self):
        """Verify zero ground-truth leakage into runtime state dictionary."""
        loader = DatasetLoader("MACHINE_001")
        loader.reset()
        state = loader.get_next_state()

        prohibited = [
            "failure_flag", "machine_status", "degradation_stage",
            "failure_type", "synthetic_health_score", "synthetic_anomaly_score",
            "failure_event_id", "time_to_failure_seconds", "failure_within_30s",
            "failure_within_60s", "_true_causes", "is_failure"
        ]
        for field in prohibited:
            self.assertNotIn(field, state, f"Ground-truth field '{field}' leaked into get_next_state()!")

    def test_06_timestamp_based_pre_failure_seeking(self):
        """Verify seek_pre_failure_by_timestamp locates position 30s before first runtime physical failure."""
        loader = DatasetLoader("MACHINE_001")
        loader.reset()
        target_idx = loader.seek_pre_failure_by_timestamp(lead_seconds=30.0)

        target_row = loader.machine_df.iloc[target_idx]
        target_time = pd.to_datetime(target_row["timestamp"])

        # First runtime physical failure is at 08:59:52 (sequence 1796, vibration > 0.35)
        first_fail_idx, first_fail_ts = failure_detector.find_first_physical_failure(loader.machine_df)
        self.assertIsNotNone(first_fail_idx)
        self.assertEqual(first_fail_ts, "2026-01-01 08:59:52")

        fail_time = pd.to_datetime(first_fail_ts)
        diff = (fail_time - target_time).total_seconds()

        self.assertGreaterEqual(diff, 28.0)
        self.assertLessEqual(diff, 32.0)
        self.assertEqual(target_idx, 1781)
        self.assertEqual(target_row["timestamp"], "2026-01-01 08:59:22")

        # Verify target row is still physically healthy (pre-failure)
        is_fail, _ = failure_detector.evaluate(PhysicalStateVector(
            timestamp=str(target_row["timestamp"]),
            device_id="SIM-ESP32",
            air_temperature=float(target_row["air_temperature"]),
            process_temperature=float(target_row["process_temperature"]),
            humidity=float(target_row["humidity"]),
            vibration=float(target_row["vibration"]),
            rotational_speed=float(target_row["rotational_speed"]),
            torque=float(target_row["torque"]),
            current=float(target_row["current"]),
            tool_wear=float(target_row["tool_wear"]),
            is_failure=False
        ), 0.84)
        self.assertFalse(is_fail, "Seek target position must be before physical failure")

    def test_07_reset_behaviour(self):
        """Verify dataset_loader reset resets index to 0."""
        loader = DatasetLoader("MACHINE_001")
        loader.current_idx = 500
        loader.reset()
        self.assertEqual(loader.current_idx, 0)
        state = loader.get_next_state()
        self.assertEqual(state["timestamp"], "2026-01-01 08:00:00")

    def test_08_anomaly_detection(self):
        """Verify IsolationForest scores normal baseline < 0.50 and anomalous > 0.80."""
        ad = AnomalyDetector()
        self.assertTrue(ad.is_trained)

        normal_psv = PhysicalStateVector(
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
        score_norm, status_norm = ad.calculate_anomaly_score(normal_psv)
        self.assertLess(score_norm, settings.WARNING_THRESHOLD)
        self.assertEqual(status_norm, "NORMAL")

        anom_psv = PhysicalStateVector(
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
        score_anom, status_anom = ad.calculate_anomaly_score(anom_psv)
        self.assertGreaterEqual(score_anom, settings.CRITICAL_THRESHOLD)
        self.assertEqual(status_anom, "CRITICAL")

    def test_09_runtime_failure_detection(self):
        """Verify FailureDetector triggers strictly on physical safety limits, not anomaly score alone."""
        fd = FailureDetector()

        # 1. Normal state -> no failure
        normal_psv = PhysicalStateVector(
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
        is_fail, _ = fd.evaluate(normal_psv, 0.20)
        self.assertFalse(is_fail)

        # 2. Critical anomaly score with normal physical parameters -> NO failure
        critical_score_psv = PhysicalStateVector(
            timestamp="2026-01-01 08:46:10",
            device_id="SIM-ESP32",
            air_temperature=22.67,
            process_temperature=44.66,
            humidity=48.2,
            vibration=0.18,
            rotational_speed=1487.4,
            torque=41.37,
            current=12.7,
            tool_wear=4.49
        )
        is_fail, details = fd.evaluate(critical_score_psv, 0.98)
        self.assertFalse(is_fail, "High anomaly score alone must not trigger physical failure")

        # 3. Thermal limit breach (process_temperature > 70°C) -> FAILURE
        thermal_psv = PhysicalStateVector(
            timestamp="2026-01-01 09:04:20",
            device_id="SIM-ESP32",
            air_temperature=22.8,
            process_temperature=75.0,
            humidity=48.3,
            vibration=0.10,
            rotational_speed=1485.0,
            torque=41.1,
            current=12.1,
            tool_wear=0.0
        )
        is_fail, details = fd.evaluate(thermal_psv, 0.70)
        self.assertTrue(is_fail)
        self.assertIn("Temperature Safety Limit Exceeded", details["reason"])

        # 4. Vibration limit breach (vibration > 0.35 mm/s) -> FAILURE
        vib_psv = PhysicalStateVector(
            timestamp="2026-01-01 09:04:20",
            device_id="SIM-ESP32",
            air_temperature=22.8,
            process_temperature=43.3,
            humidity=48.3,
            vibration=0.45,
            rotational_speed=1485.0,
            torque=41.1,
            current=12.1,
            tool_wear=0.0
        )
        is_fail, details = fd.evaluate(vib_psv, 0.70)
        self.assertTrue(is_fail)
        self.assertIn("Vibration Safety Limit Exceeded", details["reason"])

        # 5. Torque overload (torque > 75.0 Nm) -> FAILURE
        torque_psv = PhysicalStateVector(
            timestamp="2026-01-01 09:04:20",
            device_id="SIM-ESP32",
            air_temperature=22.8,
            process_temperature=43.3,
            humidity=48.3,
            vibration=0.10,
            rotational_speed=1485.0,
            torque=82.0,
            current=12.1,
            tool_wear=0.0
        )
        is_fail, details = fd.evaluate(torque_psv, 0.70)
        self.assertTrue(is_fail)
        self.assertIn("Torque Overload", details["reason"])

    def test_10_ring_buffer_locking(self):
        """Verify ring buffer records states, locks on failure, and extracts trajectory."""
        ring_buffer.reset()
        self.assertFalse(ring_buffer.is_locked)

        for i in range(20):
            temp = 43.0 + (i * 2.0)
            psv = PhysicalStateVector(
                timestamp=f"2026-01-01 08:00:{i*2:02d}",
                device_id="SIM-ESP32",
                air_temperature=23.0,
                process_temperature=temp,
                humidity=50.0,
                vibration=0.10,
                rotational_speed=1485.0,
                torque=41.0,
                current=12.0,
                tool_wear=float(i)
            )
            if temp > 70.0 and not ring_buffer.is_locked:
                psv.is_failure = True
                ring_buffer.lock({"reason": "Temperature Exceeded", "timestamp": psv.timestamp})
            ring_buffer.append(psv)

        self.assertTrue(ring_buffer.is_locked)
        self.assertIsNotNone(ring_buffer.last_extracted_trajectory)
        self.assertIsNotNone(ring_buffer.last_root_cause)
        self.assertEqual(ring_buffer.last_root_cause["ranked_causes"][0]["parameter"], "process_temperature")

    def test_11_repeated_failure_demo_execution(self):
        """Verify demonstration cycle can run repeatedly with clean state reset."""
        # Cycle 1: Trigger failure
        simulation_engine.trigger_failure()
        self.assertFalse(ring_buffer.is_locked)
        self.assertEqual(checkpoint_controller.total_states_received, 0)

        # Stream states into failure
        for _ in range(25):
            raw = dataset_loader.get_next_state()
            psv = PhysicalStateVector(
                timestamp=raw["timestamp"],
                device_id="SIM-ESP32",
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
            checkpoint_controller.evaluate(status)
            is_fail, details = failure_detector.evaluate(psv, score)
            if is_fail:
                psv.is_failure = True
                ring_buffer.lock(details)
            ring_buffer.append(psv)
            if ring_buffer.is_locked and ring_buffer.last_extracted_trajectory is not None:
                break

        self.assertTrue(ring_buffer.is_locked)
        self.assertIsNotNone(ring_buffer.last_extracted_trajectory)

        # Cycle 2: Re-trigger failure demo -> Verify completely clean reset
        simulation_engine.trigger_failure()
        self.assertFalse(ring_buffer.is_locked)
        self.assertIsNone(ring_buffer.last_extracted_trajectory)
        self.assertEqual(checkpoint_controller.total_states_received, 0)
        simulation_engine.stop()


if __name__ == "__main__":
    unittest.main()

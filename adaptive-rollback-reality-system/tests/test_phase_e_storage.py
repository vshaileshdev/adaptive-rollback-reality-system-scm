import unittest
import json
from backend.physical_state_vector import PhysicalStateVector
from backend.adaptive_snapshot_storage import AdaptiveSnapshotStorage, AdaptiveStorageConfig

class TestPhaseEStorage(unittest.TestCase):
    def setUp(self):
        self.storage = AdaptiveSnapshotStorage()
        self.base_psv_dict = {
            "timestamp": "2026-01-01 00:00:00",
            "device_id": "TEST-1",
            "air_temperature": 20.0,
            "process_temperature": 30.0,
            "humidity": 40.0,
            "vibration": 0.1,
            "rotational_speed": 1500.0,
            "torque": 20.0,
            "current": 5.0,
            "tool_wear": 10.0,
            "anomaly_score": 0.1,
            "checkpoint_level": "NORMAL",
            "machine_status": "NORMAL",
            "is_failure": False
        }

    def _create_psv(self, **kwargs):
        d = self.base_psv_dict.copy()
        d.update(kwargs)
        return PhysicalStateVector(**d)

    def test_1_first_state_full(self):
        psv = self._create_psv()
        decision = self.storage.evaluate_and_store(psv, False, False)
        self.assertEqual(decision, "FULL")
        self.assertEqual(self.storage.metrics.full_snapshots, 1)

    def test_2_stable_normal_skip(self):
        self.storage.evaluate_and_store(self._create_psv(), False, False)
        # Identical state
        decision = self.storage.evaluate_and_store(self._create_psv(), False, False)
        self.assertEqual(decision, "SKIP")
        self.assertEqual(self.storage.metrics.skipped_states, 1)

    def test_3_meaningful_change_delta(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        # Moderate plausible change: vibration increases by 30% (from 0.1 to 0.13)
        psv2 = self._create_psv(vibration=0.13, process_temperature=33.0) 
        decision = self.storage.evaluate_and_store(psv2, True, False)
        self.assertEqual(decision, "DELTA")
        self.assertEqual(self.storage.metrics.delta_snapshots, 1)

    def test_4_max_delta_chain_full(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        for i in range(AdaptiveStorageConfig.MAX_DELTA_CHAIN + 1):
            # 30% sequential increase in vibration is physically plausible up to failure
            psv = self._create_psv(vibration=0.1 * (1.3 ** (i+1))) 
            decision = self.storage.evaluate_and_store(psv, True, False)
            if i < AdaptiveStorageConfig.MAX_DELTA_CHAIN:
                self.assertEqual(decision, "DELTA", f"Failed at delta chain {i}")
            else:
                self.assertEqual(decision, "FULL", "Should force full when max chain reached")

    def test_5_warning_density(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        # WARNING state allows lower tolerance (0.02)
        psv_warn = self._create_psv(machine_status="WARNING", vibration=0.115) # 15% increase
        decision = self.storage.evaluate_and_store(psv_warn, True, False)
        self.assertEqual(decision, "DELTA")

    def test_6_critical_full(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        # CRITICAL forces FULL preservation
        psv_crit = self._create_psv(machine_status="CRITICAL", vibration=0.115)
        decision = self.storage.evaluate_and_store(psv_crit, True, False)
        self.assertEqual(decision, "FULL")

    def test_7_runtime_failure_full(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        psv_fail = self._create_psv()
        decision = self.storage.evaluate_and_store(psv_fail, True, True)
        self.assertEqual(decision, "FAILURE")
        self.assertEqual(self.storage.metrics.full_snapshots, 2)

    def test_8_ground_truth_failure_ignored(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        psv_csv_fail = self._create_psv(is_failure=True) 
        decision = self.storage.evaluate_and_store(psv_csv_fail, True, False)
        self.assertEqual(decision, "SKIP")

    def test_9_missing_optional_fields(self):
        psv = self._create_psv(current=0.0)
        self.storage.evaluate_and_store(psv, True, False)
        psv2 = self._create_psv(current=5.0)
        decision = self.storage.evaluate_and_store(psv2, True, False)
        self.assertEqual(decision, "DELTA")

    def test_10_byte_counts_deterministic(self):
        psv = self._create_psv()
        self.storage.evaluate_and_store(psv, True, False)
        m = self.storage.metrics
        self.assertGreater(m.raw_payload_bytes, 0)
        self.assertEqual(m.raw_payload_bytes, m.stored_payload_bytes)

        self.storage.evaluate_and_store(psv, True, False)
        self.assertEqual(self.storage.metrics.skipped_states, 1)
        self.assertGreater(self.storage.metrics.bytes_saved, 0)

    def test_11_storage_metrics_update(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        self.storage.evaluate_and_store(self._create_psv(vibration=0.13), True, False)
        self.assertEqual(self.storage.metrics.states_received, 2)
        self.assertEqual(self.storage.metrics.full_snapshots, 1)
        self.assertEqual(self.storage.metrics.delta_snapshots, 1)
        self.assertTrue(0 < self.storage.metrics.average_delta_bytes < self.storage.metrics.average_full_bytes)

    def test_12_snapshot_base_references(self):
        self.storage.evaluate_and_store(self._create_psv(), True, False)
        base_id = self.storage.base_full_snapshot_id
        self.assertIsNotNone(base_id)
        
        self.storage.evaluate_and_store(self._create_psv(vibration=0.13), True, False)
        self.assertEqual(self.storage.base_full_snapshot_id, base_id)
        self.assertEqual(self.storage.current_delta_chain_depth, 1)

if __name__ == '__main__':
    unittest.main()

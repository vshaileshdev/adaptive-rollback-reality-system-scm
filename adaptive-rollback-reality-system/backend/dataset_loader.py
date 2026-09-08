import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Optional

DATASET_PATH = "data/machine_timeseries.csv"

class DatasetLoader:
    def __init__(self, machine_id: str = "MACHINE_001"):
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dataset_path = os.path.join(self.base_path, DATASET_PATH)

        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Dataset not found! Please ensure {DATASET_PATH} exists.")

        self.df = pd.read_csv(self.dataset_path)
        self.selected_machine = machine_id
        self.machine_df = pd.DataFrame()
        self.current_idx = 0
        self._load_machine_data()

    def _load_machine_data(self):
        filtered = self.df[self.df["machine_id"] == self.selected_machine]
        if filtered.empty:
            raise ValueError(f"No records found for machine_id: {self.selected_machine}")
        # Ensure chronological ordering by sequence_id / timestamp
        self.machine_df = filtered.sort_values("sequence_id").reset_index(drop=True)
        self.current_idx = 0

    def select_machine(self, machine_id: str):
        """Switch active machine stream while preserving chronological ordering."""
        self.selected_machine = machine_id
        self._load_machine_data()

    def get_next_state(self) -> Dict[str, Any]:
        """
        Yields the next chronological physical telemetry record.
        Strictly excludes ground-truth labels and mock random telemetry.
        """
        if self.current_idx >= len(self.machine_df):
            self.current_idx = 0  # Loop back to beginning for continuous simulation

        row = self.machine_df.iloc[self.current_idx]
        self.current_idx += 1

        return {
            "timestamp": str(row["timestamp"]),
            "machine_id": str(row["machine_id"]),
            "air_temperature": float(row["air_temperature"]),
            "process_temperature": float(row["process_temperature"]),
            "humidity": float(row["humidity"]),
            "vibration": float(row["vibration"]),
            "rotational_speed": float(row["rotational_speed"]),
            "torque": float(row["torque"]),
            "tool_wear": float(row["tool_wear"]),
            "current": float(row["current"]),
        }

    def seek_pre_failure_by_timestamp(self, lead_seconds: float = 30.0) -> int:
        """
        Determines the first runtime physical failure position dynamically using
        FailureDetector rules, calculates target timestamp = failure_timestamp - lead_seconds,
        and sets playback position to the nearest chronological row at or before target.
        """
        from .failure_detector import failure_detector
        _, fail_timestamp_str = failure_detector.find_first_physical_failure(self.machine_df)

        if fail_timestamp_str is None:
            # Fallback to offline ground truth if no physical rule tripped
            failure_rows = self.machine_df[
                (self.machine_df["failure_flag"] == 1) |
                (self.machine_df["machine_status"] == "FAILURE")
            ]
            if failure_rows.empty:
                self.current_idx = 0
                return 0
            fail_timestamp_str = str(failure_rows.iloc[0]["timestamp"])

        failure_time = pd.to_datetime(fail_timestamp_str)
        target_time = failure_time - pd.Timedelta(seconds=lead_seconds)

        # Convert series timestamps to datetime for accurate nearest-search
        ts_series = pd.to_datetime(self.machine_df["timestamp"])
        pre_failure_candidates = self.machine_df[ts_series <= target_time]

        if not pre_failure_candidates.empty:
            target_idx = pre_failure_candidates.index[-1]
        else:
            target_idx = 0

        self.current_idx = int(target_idx)
        return self.current_idx

    def get_normal_baseline(self, n_samples: Optional[int] = None) -> np.ndarray:
        """
        Returns chronological normal operational baseline features for AnomalyDetector fitting.
        Uses ALL available healthy rows where degradation_stage == 0 (or up to n_samples if specified).
        """
        normal_slice = self.machine_df[self.machine_df["degradation_stage"] == 0]
        if normal_slice.empty:
            normal_slice = self.machine_df.head(n_samples if n_samples else 200)
        elif n_samples is not None:
            normal_slice = normal_slice.head(n_samples)

        features = normal_slice[[
            "air_temperature",
            "process_temperature",
            "rotational_speed",
            "torque",
            "vibration"
        ]].to_numpy()
        return features

    def reset(self):
        """Resets playback index to start of chronological stream."""
        self.current_idx = 0

dataset_loader = DatasetLoader()

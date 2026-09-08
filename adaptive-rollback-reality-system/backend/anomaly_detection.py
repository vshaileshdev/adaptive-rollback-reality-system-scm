import numpy as np
from sklearn.ensemble import IsolationForest
from .config import settings
from .dataset_loader import dataset_loader

class AnomalyDetector:
    def __init__(self):
        # Using IsolationForest for anomaly detection on clean normal baseline
        self.model = IsolationForest(contamination="auto", random_state=42)
        self.is_trained = False
        self._train_baseline()

    def _train_baseline(self):
        try:
            baseline_data = dataset_loader.get_normal_baseline()
            if len(baseline_data) > 0:
                self.model.fit(baseline_data)
                self.is_trained = True
                return
        except Exception as e:
            print(f"Warning: Failed to load baseline from dataset: {e}")

        # Fallback baseline with expected physical ranges if dataset unavailable during init
        dummy_data = np.array([
            [22.8, 43.3, 1485.0, 41.0, 0.10],
            [22.9, 43.5, 1486.0, 41.2, 0.10],
            [22.7, 43.2, 1484.0, 40.9, 0.11],
            [22.8, 43.4, 1485.5, 41.1, 0.09],
            [22.8, 43.3, 1485.0, 41.0, 0.10]
        ])
        self.model.fit(dummy_data)
        self.is_trained = True

    def calculate_anomaly_score(self, psv) -> tuple[float, str]:
        """
        Takes a PhysicalStateVector and returns (normalized_score, status).
        Normalized score is between 0.0 and 1.0.
        Purely physical calculation without ground-truth label overrides.
        """
        # Features to analyze (5-feature vector preserved)
        features = np.array([[
            psv.air_temperature,
            psv.process_temperature,
            psv.rotational_speed,
            psv.torque,
            psv.vibration
        ]])

        raw_score = self.model.decision_function(features)[0]

        # Normalize decision function to [0, 1]
        # In scikit-learn Isolation Forest, raw_score is positive (~0.05) for normal baseline
        # and negative (~ -0.15) for severe anomalous deviations.
        normalized_score = 0.5 - (raw_score * 3.5)
        normalized_score = max(0.0, min(1.0, float(normalized_score)))

        status = "NORMAL"
        if normalized_score >= settings.CRITICAL_THRESHOLD:
            status = "CRITICAL"
        elif normalized_score >= settings.WARNING_THRESHOLD:
            status = "WARNING"

        return float(normalized_score), status

detector = AnomalyDetector()

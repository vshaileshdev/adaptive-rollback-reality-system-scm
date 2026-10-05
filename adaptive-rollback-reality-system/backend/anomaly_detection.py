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
            if len(baseline_data) == 0:
                raise ValueError("Baseline dataset is empty.")
            
            self.model.fit(baseline_data)
            self.is_trained = True
            
            # Calculate and store baseline statistics for root cause analysis
            self.baseline_stats = {
                "air_temperature": {"mean": np.mean(baseline_data[:, 0]), "std": np.std(baseline_data[:, 0])},
                "process_temperature": {"mean": np.mean(baseline_data[:, 1]), "std": np.std(baseline_data[:, 1])},
                "rotational_speed": {"mean": np.mean(baseline_data[:, 2]), "std": np.std(baseline_data[:, 2])},
                "torque": {"mean": np.mean(baseline_data[:, 3]), "std": np.std(baseline_data[:, 3])},
                "vibration": {"mean": np.mean(baseline_data[:, 4]), "std": np.std(baseline_data[:, 4])}
            }
        except Exception as e:
            raise RuntimeError(f"Initialization Error: A verified normal baseline is required. Failed to load baseline from dataset: {e}")

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

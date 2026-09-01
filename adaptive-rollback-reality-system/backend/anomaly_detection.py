import numpy as np
from sklearn.ensemble import IsolationForest
from .config import settings

class AnomalyDetector:
    def __init__(self):
        # Using IsolationForest for anomaly detection
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
        
        # We need some initial dummy data to fit the model so it can predict
        # Normally this would be trained on historical normal data
        dummy_data = np.array([
            [30.0, 40.0, 1500.0, 40.0, 0.1],
            [30.1, 40.2, 1505.0, 40.5, 0.11],
            [29.9, 39.8, 1495.0, 39.5, 0.09],
            [30.0, 40.0, 1500.0, 40.0, 0.1],
            [30.2, 40.1, 1510.0, 41.0, 0.12]
        ])
        self.model.fit(dummy_data)
        self.is_trained = True

    def calculate_anomaly_score(self, psv) -> tuple[float, str]:
        """
        Takes a PhysicalStateVector and returns (normalized_score, status)
        normalized_score is between 0.0 and 1.0
        """
        # Features to analyze
        features = np.array([[
            psv.air_temperature,
            psv.process_temperature,
            psv.rotational_speed,
            psv.torque,
            psv.vibration
        ]])
        
        # decision_function returns lower values for anomalies (often negative)
        # and higher values for normal points.
        # We want to map this to an anomaly score from 0 to 1 where 1 is highly anomalous.
        raw_score = self.model.decision_function(features)[0]
        
        # Normalize: Isolation forest decision function is usually between -0.5 and 0.5
        # We can map it loosely: score = 0.5 - raw_score (clamped to 0, 1)
        # This is a heuristic mapping for demonstration purposes.
        normalized_score = 0.5 - raw_score
        normalized_score = max(0.0, min(1.0, normalized_score))
        
        # Override with explicit dataset-provided logic if available or failure state
        if psv.is_failure:
            normalized_score = 1.0
            
        status = "NORMAL"
        if normalized_score >= settings.CRITICAL_THRESHOLD:
            status = "CRITICAL"
        elif normalized_score >= settings.WARNING_THRESHOLD:
            status = "WARNING"
            
        return float(normalized_score), status

detector = AnomalyDetector()

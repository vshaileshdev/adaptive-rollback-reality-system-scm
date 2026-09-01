from .physical_state_vector import PhysicalStateVector
from .config import settings

class FailureDetector:
    def evaluate(self, psv: PhysicalStateVector, normalized_score: float) -> tuple[bool, dict]:
        """
        Returns (is_failure, failure_details_dict)
        """
        # A dataset explicitly telling us it's a failure
        if psv.is_failure:
            return True, {
                "reason": "Dataset Label",
                "score": 1.0,
                "timestamp": psv.timestamp
            }
            
        # Or anomaly score is above critical
        # Actually in this system, maybe CRITICAL state means we check failure?
        # The prompt says: Trigger failure if anomaly > critical OR safety limits exceeded.
        # Let's say anomaly_score > 0.95 is a failure
        if normalized_score >= 0.95:
            return True, {
                "reason": "Critical Anomaly Score",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }
            
        # Hard safety limits (example bounds based on typical AI4I dataset values)
        if psv.air_temperature > 310.0 or psv.process_temperature > 320.0:
            return True, {
                "reason": "Temperature Safety Limit Exceeded",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }
            
        if psv.rotational_speed > 2900 or psv.rotational_speed < 1100:
            return True, {
                "reason": "Rotational Speed Out of Bounds",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }
            
        if psv.torque > 75.0:
            return True, {
                "reason": "Torque Overload",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }

        return False, {}

failure_detector = FailureDetector()

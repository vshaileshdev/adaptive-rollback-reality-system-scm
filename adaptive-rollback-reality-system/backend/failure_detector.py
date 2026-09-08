from .physical_state_vector import PhysicalStateVector
from .config import settings

class FailureDetector:
    def evaluate(self, psv: PhysicalStateVector, normalized_score: float) -> tuple[bool, dict]:
        """
        Evaluates runtime physical telemetry for actual physical failure conditions.
        Returns (is_failure, failure_details_dict).
        Anomaly score drives adaptive checkpointing; physical limits drive failure state.
        """
        # 1. Temperature Safety Limits (Celsius)
        if (psv.air_temperature > settings.MAX_AIR_TEMP_CELSIUS or
            psv.process_temperature > settings.MAX_PROCESS_TEMP_CELSIUS):
            return True, {
                "reason": "Temperature Safety Limit Exceeded",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }

        # 3. Vibration Safety Limit (RMS mm/s)
        if psv.vibration > settings.MAX_VIBRATION_RMS:
            return True, {
                "reason": "Vibration Safety Limit Exceeded",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }

        # 4. Rotational Speed Limits (RPM)
        if (psv.rotational_speed > settings.MAX_SPEED_RPM or
            psv.rotational_speed < settings.MIN_SPEED_RPM):
            return True, {
                "reason": "Rotational Speed Out of Bounds",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }

        # 5. Torque Overload (Nm)
        if psv.torque > settings.MAX_TORQUE_NM:
            return True, {
                "reason": "Torque Overload",
                "score": normalized_score,
                "timestamp": psv.timestamp
            }

        return False, {}

    def find_first_physical_failure(self, df) -> tuple:
        """
        Scans a dataframe chronologically using the physical safety limits
        to find the first failure row index and timestamp.
        Returns (first_idx, first_timestamp_str) or (None, None).
        """
        mask = (
            (df["air_temperature"] > settings.MAX_AIR_TEMP_CELSIUS) |
            (df["process_temperature"] > settings.MAX_PROCESS_TEMP_CELSIUS) |
            (df["vibration"] > settings.MAX_VIBRATION_RMS) |
            (df["rotational_speed"] > settings.MAX_SPEED_RPM) |
            (df["rotational_speed"] < settings.MIN_SPEED_RPM) |
            (df["torque"] > settings.MAX_TORQUE_NM)
        )
        matches = df[mask]
        if not matches.empty:
            first_idx = int(matches.index[0])
            return first_idx, str(matches.iloc[0]["timestamp"])
        return None, None

failure_detector = FailureDetector()

from datetime import datetime
from typing import Optional, Union, Dict, List
from .config import settings

STATUS_SEVERITY = {
    "NORMAL": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "FAILURE": 3
}

class CheckpointController:
    def __init__(self):
        self.state_counter = 0
        self.total_states_received = 0
        self.total_checkpoints_saved = 0
        self.last_checkpoint_timestamp: Optional[datetime] = None
        self.last_status: Optional[str] = None
        self.checkpoints_by_status: Dict[str, int] = {
            "NORMAL": 0,
            "WARNING": 0,
            "CRITICAL": 0,
            "FAILURE": 0
        }
        self.states_by_status: Dict[str, int] = {
            "NORMAL": 0,
            "WARNING": 0,
            "CRITICAL": 0,
            "FAILURE": 0
        }
        self.interval_history: Dict[str, List[float]] = {
            "NORMAL": [],
            "WARNING": [],
            "CRITICAL": []
        }

    def evaluate(self, status: str, anomaly_score: float = 0.0, timestamp: Optional[Union[str, datetime]] = None) -> tuple[float, bool]:
        """
        Evaluates whether the incoming telemetry state warrants a checkpoint.
        Uses continuous anomaly score to dynamically map to target logical intervals.
        """
        self.total_states_received += 1
        norm_status = status if status in self.states_by_status else "NORMAL"
        self.states_by_status[norm_status] = self.states_by_status.get(norm_status, 0) + 1

        should_save = False
        current_dt: Optional[datetime] = None

        if timestamp is not None:
            if isinstance(timestamp, str):
                try:
                    current_dt = datetime.fromisoformat(timestamp)
                except Exception:
                    current_dt = None
            elif isinstance(timestamp, datetime):
                current_dt = timestamp

        # Determine target_interval continuously from anomaly_score (0.0 to 1.0)
        max_interval = settings.NORMAL_CHECKPOINT_INTERVAL_SEC
        min_interval = settings.CRITICAL_CHECKPOINT_INTERVAL_SEC
        if status == "FAILURE":
            target_interval = 0.0
        else:
            # Linear interpolation based on anomaly score
            target_interval = max_interval - (anomaly_score * (max_interval - min_interval))
            target_interval = max(min_interval, min(max_interval, target_interval))

        if current_dt is not None:
            if self.last_checkpoint_timestamp is None:
                # First received telemetry state is always checkpointed
                should_save = True
            else:
                elapsed = (current_dt - self.last_checkpoint_timestamp).total_seconds()

                # Status escalation trigger: capture transitions to higher risk immediately
                current_severity = STATUS_SEVERITY.get(norm_status, 0)
                last_severity = STATUS_SEVERITY.get(self.last_status, 0) if self.last_status else 0
                escalated = current_severity > last_severity

                if elapsed >= target_interval or escalated:
                    should_save = True
                    if self.last_status == norm_status and norm_status in self.interval_history and not escalated:
                        self.interval_history[norm_status].append(elapsed)
        else:
            # Fallback to modulo state count for callers without timestamps
            self.state_counter += 1
            if status == "CRITICAL":
                freq = settings.CRITICAL_CHECKPOINT_FREQ
            elif status == "WARNING":
                freq = settings.WARNING_CHECKPOINT_FREQ
            else:
                freq = settings.NORMAL_CHECKPOINT_FREQ
            if self.state_counter >= freq:
                should_save = True
                self.state_counter = 0

        if should_save:
            self.total_checkpoints_saved += 1
            self.checkpoints_by_status[norm_status] = self.checkpoints_by_status.get(norm_status, 0) + 1
            if current_dt is not None:
                self.last_checkpoint_timestamp = current_dt
            self.last_status = norm_status

        return float(target_interval), should_save

    def record_failure(self, timestamp: Optional[Union[str, datetime]] = None):
        """Explicitly records and preserves the terminal physical failure checkpoint."""
        current_dt = None
        if isinstance(timestamp, str):
            try:
                current_dt = datetime.fromisoformat(timestamp)
            except Exception:
                pass
        elif isinstance(timestamp, datetime):
            current_dt = timestamp

        self.total_checkpoints_saved += 1
        self.checkpoints_by_status["FAILURE"] = self.checkpoints_by_status.get("FAILURE", 0) + 1
        if current_dt:
            self.last_checkpoint_timestamp = current_dt
        self.last_status = "FAILURE"

    def get_metrics(self) -> dict:
        """
        Returns comprehensive measurable runtime metrics including baseline comparison,
        storage reduction percentages, compression ratio, and interval averages.
        """
        storage_saved = max(0, self.total_states_received - self.total_checkpoints_saved)
        reduction_pct = (
            (storage_saved / self.total_states_received * 100.0)
            if self.total_states_received > 0 else 0.0
        )
        reduction_ratio = (
            (self.total_states_received / self.total_checkpoints_saved)
            if self.total_checkpoints_saved > 0 else 1.0
        )

        effective_intervals = {}
        for k, v in self.interval_history.items():
            if v:
                effective_intervals[k] = round(sum(v) / len(v), 2)
            else:
                effective_intervals[k] = round(getattr(settings, f"{k}_CHECKPOINT_INTERVAL_SEC"), 1)

        return {
            "total_states_received": self.total_states_received,
            "total_checkpoints": self.total_checkpoints_saved,
            "storage_saved": storage_saved,
            "storage_reduction_percent": round(reduction_pct, 2),
            "storage_reduction_ratio": round(reduction_ratio, 2),
            "checkpoints_by_status": dict(self.checkpoints_by_status),
            "states_by_status": dict(self.states_by_status),
            "effective_intervals": effective_intervals,
            "target_intervals": {
                "NORMAL": settings.NORMAL_CHECKPOINT_INTERVAL_SEC,
                "WARNING": settings.WARNING_CHECKPOINT_INTERVAL_SEC,
                "CRITICAL": settings.CRITICAL_CHECKPOINT_INTERVAL_SEC
            }
        }

    def reset(self):
        """Cleanly resets all runtime counters, metrics, and interval histories."""
        self.state_counter = 0
        self.total_states_received = 0
        self.total_checkpoints_saved = 0
        self.last_checkpoint_timestamp = None
        self.last_status = None
        self.checkpoints_by_status = {
            "NORMAL": 0,
            "WARNING": 0,
            "CRITICAL": 0,
            "FAILURE": 0
        }
        self.states_by_status = {
            "NORMAL": 0,
            "WARNING": 0,
            "CRITICAL": 0,
            "FAILURE": 0
        }
        self.interval_history = {
            "NORMAL": [],
            "WARNING": [],
            "CRITICAL": []
        }

checkpoint_controller = CheckpointController()

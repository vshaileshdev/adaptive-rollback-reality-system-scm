import os
from pydantic import BaseModel

class Config(BaseModel):
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./database/machine_data.db")

    # Anomaly thresholds
    WARNING_THRESHOLD: float = 0.50
    CRITICAL_THRESHOLD: float = 0.80

    # Checkpoint frequencies (fallback / state counts)
    NORMAL_CHECKPOINT_FREQ: int = 10
    WARNING_CHECKPOINT_FREQ: int = 5
    CRITICAL_CHECKPOINT_FREQ: int = 1

    # Logical Checkpoint Target Intervals (Dataset Timeline Seconds)
    # Note: 1.0s in CRITICAL is a logical maximum interval. Because dataset arrives every 2s,
    # every available telemetry sample (1 sample) is saved in CRITICAL mode.
    NORMAL_CHECKPOINT_INTERVAL_SEC: float = 10.0
    WARNING_CHECKPOINT_INTERVAL_SEC: float = 5.0
    CRITICAL_CHECKPOINT_INTERVAL_SEC: float = 1.0

    # Ring Buffer
    RING_BUFFER_CAPACITY: int = 100

    # Trajectory Extraction
    PRE_FAILURE_WINDOW: int = 10
    POST_FAILURE_WINDOW: int = 5

    # Physical Safety Thresholds (Celsius & Metric)
    MAX_PROCESS_TEMP_CELSIUS: float = 70.0
    MAX_AIR_TEMP_CELSIUS: float = 40.0
    MAX_TORQUE_NM: float = 75.0
    MIN_SPEED_RPM: float = 1100.0
    MAX_SPEED_RPM: float = 2900.0
    MAX_VIBRATION_RMS: float = 0.35

    # Failure Demonstration Positioning
    PRE_FAILURE_LEAD_SECONDS: float = 30.0

settings = Config()

import os
from pydantic import BaseModel

class Config(BaseModel):
    DATABASE_URL: str = "sqlite:///./database/machine_data.db"
    
    # Anomaly thresholds
    WARNING_THRESHOLD: float = 0.50
    CRITICAL_THRESHOLD: float = 0.80
    
    # Checkpoint frequencies
    NORMAL_CHECKPOINT_FREQ: int = 10
    WARNING_CHECKPOINT_FREQ: int = 5
    CRITICAL_CHECKPOINT_FREQ: int = 1
    
    # Ring Buffer
    RING_BUFFER_CAPACITY: int = 100
    
    # Trajectory Extraction
    PRE_FAILURE_WINDOW: int = 10
    POST_FAILURE_WINDOW: int = 5

settings = Config()

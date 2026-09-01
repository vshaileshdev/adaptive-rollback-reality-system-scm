from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PhysicalStateVector(BaseModel):
    timestamp: str
    device_id: str
    air_temperature: float
    process_temperature: float
    humidity: float
    vibration: float
    rotational_speed: float
    torque: float
    current: float
    tool_wear: float
    anomaly_score: float = 0.0
    checkpoint_level: str = "NORMAL"
    machine_status: str = "NORMAL"
    is_failure: bool = False

class IoTPayload(BaseModel):
    device_id: str
    timestamp: str
    temperature: float # mapped to air_temperature
    humidity: float
    vibration: float
    current: Optional[float] = 0.0
    speed: Optional[float] = 0.0 # mapped to rotational_speed
    torque: Optional[float] = 0.0
    
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from .database import Base

class MachineStateDB(Base):
    __tablename__ = "machine_states"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, index=True)
    device_id = Column(String, index=True)
    air_temperature = Column(Float)
    process_temperature = Column(Float)
    humidity = Column(Float)
    vibration = Column(Float)
    rotational_speed = Column(Float)
    torque = Column(Float)
    current = Column(Float)
    tool_wear = Column(Float)
    anomaly_score = Column(Float)
    checkpoint_level = Column(String)
    machine_status = Column(String)
    is_failure = Column(Boolean, default=False)

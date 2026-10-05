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
    acceleration_x: Optional[float] = None
    acceleration_y: Optional[float] = None
    acceleration_z: Optional[float] = None
    acceleration_magnitude: Optional[float] = None
    voltage: Optional[float] = None
    mechanical_position: Optional[float] = None
    controller_state: Optional[str] = None
    actuator_state: Optional[str] = None
    machine_operating_mode: Optional[str] = None

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
    acceleration_x = Column(Float, nullable=True)
    acceleration_y = Column(Float, nullable=True)
    acceleration_z = Column(Float, nullable=True)
    acceleration_magnitude = Column(Float, nullable=True)
    voltage = Column(Float, nullable=True)
    mechanical_position = Column(Float, nullable=True)
    controller_state = Column(String, nullable=True)
    actuator_state = Column(String, nullable=True)
    machine_operating_mode = Column(String, nullable=True)

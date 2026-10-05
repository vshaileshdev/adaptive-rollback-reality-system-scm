import json
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Text

from .database import Base, SessionLocal
from .physical_state_vector import PhysicalStateVector

class SnapshotDB(Base):
    __tablename__ = "adaptive_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, index=True)
    timestamp = Column(String, index=True)
    snapshot_type = Column(String) # FULL, DELTA, FAILURE
    base_snapshot_id = Column(Integer, nullable=True)
    changed_fields = Column(Text, nullable=True)
    storage_bytes = Column(Integer, default=0)
    raw_state_bytes = Column(Integer, default=0)
    change_score = Column(Float, default=0.0)
    decision_reason = Column(String, nullable=True)
    machine_status = Column(String, nullable=True)
    anomaly_score = Column(Float, default=0.0)

class AdaptiveStorageConfig:
    MAX_DELTA_CHAIN: int = 10
    TOLERANCE_NORMAL: float = 0.05
    TOLERANCE_WARNING: float = 0.02
    TOLERANCE_CRITICAL: float = 0.0
    
    # Weights for change score
    WEIGHTS = {
        "air_temperature": 1.0,
        "process_temperature": 1.0,
        "vibration": 1.5,
        "rotational_speed": 1.0,
        "torque": 1.0,
        "current": 1.0,
        "tool_wear": 1.0
    }

class StorageMetrics(BaseModel):
    states_received: int = 0
    snapshots_stored: int = 0
    full_snapshots: int = 0
    delta_snapshots: int = 0
    skipped_states: int = 0
    raw_payload_bytes: int = 0
    stored_payload_bytes: int = 0
    bytes_saved: int = 0
    storage_reduction_percent: float = 0.0
    average_full_bytes: float = 0.0
    average_delta_bytes: float = 0.0
    average_change_score: float = 0.0

class AdaptiveSnapshotStorage:
    def __init__(self):
        self.metrics = StorageMetrics()
        self.last_retained_snapshot_psv: Optional[PhysicalStateVector] = None
        self.last_retained_snapshot_id: Optional[int] = None
        self.base_full_snapshot_id: Optional[int] = None
        self.current_delta_chain_depth: int = 0
        self.total_full_bytes: int = 0
        self.total_delta_bytes: int = 0
        self.total_change_score: float = 0.0
        self.score_count: int = 0

    def calculate_change_score(self, current_psv: PhysicalStateVector, last_psv: PhysicalStateVector) -> Tuple[float, Dict[str, Any]]:
        score = 0.0
        total_weight = 0.0
        changed_fields = {}
        
        for field, weight in AdaptiveStorageConfig.WEIGHTS.items():
            curr_val = getattr(current_psv, field, None)
            last_val = getattr(last_psv, field, None)
            
            if curr_val is not None and last_val is not None:
                if last_val != 0:
                    diff_ratio = abs(curr_val - last_val) / abs(last_val)
                else:
                    diff_ratio = abs(curr_val - last_val) # Absolute diff if last is 0
                
                score += diff_ratio * weight
                total_weight += weight
                
                # If difference is non-zero, record it for delta
                if curr_val != last_val:
                    changed_fields[field] = curr_val
                    
        normalized_score = score / total_weight if total_weight > 0 else 0.0
        return normalized_score, changed_fields

    def evaluate_and_store(self, psv: PhysicalStateVector, interval_due_should_save: bool, is_failure: bool) -> str:
        self.metrics.states_received += 1
        
        raw_state_dict = psv.model_dump()
        raw_state_json = json.dumps(raw_state_dict)
        raw_bytes = len(raw_state_json.encode('utf-8'))
        self.metrics.raw_payload_bytes += raw_bytes
        
        decision = "SKIP"
        decision_reason = "No meaningful change"
        change_score = 0.0
        changed_fields = raw_state_dict # Default to full for FULL/FAILURE
        
        # 1. First state or Failure
        if self.last_retained_snapshot_psv is None:
            decision = "FULL"
            decision_reason = "First state"
        elif is_failure:
            decision = "FAILURE"
            decision_reason = "Runtime failure detected"
        elif not interval_due_should_save:
            # CheckpointController policy says no checkpoint needed yet
            decision = "SKIP"
            decision_reason = "Checkpoint interval not reached"
        else:
            # CheckpointController requested a checkpoint. Storage decides representation.
            change_score, delta_fields = self.calculate_change_score(psv, self.last_retained_snapshot_psv)
            self.total_change_score += change_score
            self.score_count += 1
            
            if self.current_delta_chain_depth >= AdaptiveStorageConfig.MAX_DELTA_CHAIN:
                decision = "FULL"
                decision_reason = "Max delta chain reached"
            elif psv.machine_status == "CRITICAL":
                decision = "FULL"
                decision_reason = "Critical state dense checkpointing"
            else:
                # Decide if meaningful enough to store as DELTA, or SKIP to save storage
                tolerance = AdaptiveStorageConfig.TOLERANCE_WARNING if psv.machine_status == "WARNING" else AdaptiveStorageConfig.TOLERANCE_NORMAL
                if change_score > tolerance:
                    decision = "DELTA"
                    decision_reason = f"Meaningful change ({psv.machine_status})"
                    changed_fields = delta_fields
                else:
                    decision = "SKIP"
                    decision_reason = "No meaningful change"

        if decision == "SKIP":
            self.metrics.skipped_states += 1
            self.metrics.bytes_saved += raw_bytes
            self._update_percentages()
            return decision

        # WE ARE SAVING A SNAPSHOT (FULL, FAILURE, or DELTA)
        self.metrics.snapshots_stored += 1
        
        stored_type = "FULL" if decision in ("FULL", "FAILURE") else "DELTA"
        if decision == "FAILURE":
            stored_type = "FAILURE"
            
        is_full = stored_type in ("FULL", "FAILURE")
        
        if is_full:
            self.metrics.full_snapshots += 1
            self.current_delta_chain_depth = 0
            base_id = None
        else:
            self.metrics.delta_snapshots += 1
            self.current_delta_chain_depth += 1
            base_id = self.base_full_snapshot_id

        # Calculate storage bytes
        # For FULL, we store the full raw_state_dict. For DELTA, only changed_fields
        storage_payload = json.dumps(changed_fields)
        storage_bytes = len(storage_payload.encode('utf-8'))
        
        self.metrics.stored_payload_bytes += storage_bytes
        self.metrics.bytes_saved += (raw_bytes - storage_bytes)
        
        if is_full:
            self.total_full_bytes += storage_bytes
        else:
            self.total_delta_bytes += storage_bytes

        # Database Insertion
        db = SessionLocal()
        try:
            snapshot = SnapshotDB(
                machine_id=psv.device_id,
                timestamp=psv.timestamp,
                snapshot_type=stored_type,
                base_snapshot_id=base_id,
                changed_fields=storage_payload,
                storage_bytes=storage_bytes,
                raw_state_bytes=raw_bytes,
                change_score=change_score,
                decision_reason=decision_reason,
                machine_status=psv.machine_status,
                anomaly_score=psv.anomaly_score
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            
            self.last_retained_snapshot_id = snapshot.id
            if is_full:
                self.base_full_snapshot_id = snapshot.id
                
        finally:
            db.close()

        # Update Last Retained
        self.last_retained_snapshot_psv = psv
        
        self._update_percentages()
        return decision
        
    def _update_percentages(self):
        if self.metrics.raw_payload_bytes > 0:
            self.metrics.storage_reduction_percent = (self.metrics.bytes_saved / self.metrics.raw_payload_bytes) * 100.0
            
        if self.metrics.full_snapshots > 0:
            self.metrics.average_full_bytes = self.total_full_bytes / self.metrics.full_snapshots
            
        if self.metrics.delta_snapshots > 0:
            self.metrics.average_delta_bytes = self.total_delta_bytes / self.metrics.delta_snapshots
            
        if self.score_count > 0:
            self.metrics.average_change_score = self.total_change_score / self.score_count

    def reset(self):
        self.metrics = StorageMetrics()
        self.last_retained_snapshot_psv = None
        self.last_retained_snapshot_id = None
        self.base_full_snapshot_id = None
        self.current_delta_chain_depth = 0
        self.total_full_bytes = 0
        self.total_delta_bytes = 0
        self.total_change_score = 0.0
        self.score_count = 0

storage_engine = AdaptiveSnapshotStorage()

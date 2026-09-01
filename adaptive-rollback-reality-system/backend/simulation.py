import asyncio
from datetime import datetime
import uuid

from .dataset_loader import dataset_loader
from .physical_state_vector import PhysicalStateVector, MachineStateDB
from .anomaly_detection import detector
from .checkpoint_controller import checkpoint_controller
from .ring_buffer import ring_buffer
from .failure_detector import failure_detector
from .websocket_manager import manager
from .database import SessionLocal

class SimulationEngine:
    def __init__(self):
        self.is_running = False
        self.task = None

    async def _simulation_loop(self):
        while self.is_running:
            try:
                # 1. Get next state from dataset
                raw_data = dataset_loader.get_next_state()
                
                # 2. Build PSV
                psv = PhysicalStateVector(
                    timestamp=datetime.utcnow().isoformat(),
                    device_id="SIM-ESP32",
                    air_temperature=raw_data["air_temperature"],
                    process_temperature=raw_data["process_temperature"],
                    humidity=50.0,
                    vibration=raw_data["vibration"],
                    rotational_speed=raw_data["rotational_speed"],
                    torque=raw_data["torque"],
                    current=raw_data["current"],
                    tool_wear=raw_data["tool_wear"],
                    is_failure=raw_data["is_failure"]
                )
                
                # 3. Anomaly detection
                score, status = detector.calculate_anomaly_score(psv)
                psv.anomaly_score = score
                
                # 4. Checkpoint controller
                freq, should_save = checkpoint_controller.evaluate(status)
                psv.checkpoint_level = status
                psv.machine_status = status
                
                # 5. Failure detection
                is_fail, fail_details = failure_detector.evaluate(psv, score)
                if is_fail:
                    psv.machine_status = "FAILURE"
                    psv.is_failure = True
                    ring_buffer.lock(fail_details)
                
                # 6. Ring buffer
                ring_buffer.append(psv)
                
                # 7. Optionally save to DB (only if checkpoint says so)
                if should_save:
                    db = SessionLocal()
                    db_state = MachineStateDB(**psv.model_dump())
                    db.add(db_state)
                    db.commit()
                    db.close()
                
                # 8. Broadcast state
                await manager.broadcast_state({
                    "type": "state_update",
                    "data": psv.model_dump(),
                    "metrics": checkpoint_controller.get_metrics(),
                    "buffer_locked": ring_buffer.is_locked,
                    "failure_event": ring_buffer.failure_event,
                    "trajectory_ready": ring_buffer.last_extracted_trajectory is not None
                })
                
                # We slow it down slightly for visual effect
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Simulation error: {e}")
                self.is_running = False
                break

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._simulation_loop())

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            
    def trigger_failure(self):
        # fast forward to dataset index near 990 where failure starts
        dataset_loader.current_idx = 990
        self.start()

simulation_engine = SimulationEngine()

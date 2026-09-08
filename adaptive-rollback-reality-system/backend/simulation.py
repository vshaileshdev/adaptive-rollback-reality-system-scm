import asyncio
from datetime import datetime
import uuid

from .config import settings
from .dataset_loader import dataset_loader
from .physical_state_vector import PhysicalStateVector, MachineStateDB
from .anomaly_detection import detector
from .checkpoint_controller import checkpoint_controller
from .ring_buffer import ring_buffer
from .replay_engine import replay_engine
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
                # 1. Get next state from dataset (pure physical telemetry)
                raw_data = dataset_loader.get_next_state()

                # 2. Build PSV (is_failure initialized False, never copied from ground truth)
                psv = PhysicalStateVector(
                    timestamp=raw_data["timestamp"],
                    device_id=raw_data.get("machine_id", "SIM-ESP32"),
                    air_temperature=raw_data["air_temperature"],
                    process_temperature=raw_data["process_temperature"],
                    humidity=raw_data["humidity"],
                    vibration=raw_data["vibration"],
                    rotational_speed=raw_data["rotational_speed"],
                    torque=raw_data["torque"],
                    current=raw_data["current"],
                    tool_wear=raw_data["tool_wear"],
                    is_failure=False
                )

                # 3. Anomaly detection (evaluated purely on physical telemetry)
                score, status = detector.calculate_anomaly_score(psv)
                psv.anomaly_score = score

                # 4. Checkpoint controller
                freq, should_save = checkpoint_controller.evaluate(status)
                psv.checkpoint_level = status
                psv.machine_status = status

                # 5. Failure detection (driven strictly by physical limits & critical anomaly scores)
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

                # Separation of playback pacing (0.1s tick) from dataset timestamp
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Simulation error: {e}")
                self.is_running = False
                break

    def start(self):
        if not self.is_running:
            self.is_running = True
            try:
                loop = asyncio.get_running_loop()
                self.task = loop.create_task(self._simulation_loop())
            except RuntimeError:
                # No running event loop (e.g. synchronous testing context)
                self.task = None

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None

    def trigger_failure(self):
        """
        Cleanly resets all active runtime state, seeks to the timestamp-based
        pre-failure window, and restarts playback for an autonomous detection demo.
        """
        self.stop()
        ring_buffer.reset()
        checkpoint_controller.reset()
        replay_engine.reset()
        dataset_loader.seek_pre_failure_by_timestamp(lead_seconds=settings.PRE_FAILURE_LEAD_SECONDS)
        self.start()

    def reset(self):
        """Full simulation and runtime state reset."""
        self.stop()
        dataset_loader.reset()
        ring_buffer.reset()
        checkpoint_controller.reset()
        replay_engine.reset()

simulation_engine = SimulationEngine()

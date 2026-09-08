from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import engine, Base, get_db, SessionLocal
from .physical_state_vector import IoTPayload, PhysicalStateVector, MachineStateDB
from .websocket_manager import manager
from .simulation import simulation_engine
from .anomaly_detection import detector
from .checkpoint_controller import checkpoint_controller
from .ring_buffer import ring_buffer
from .replay_engine import replay_engine
from .failure_detector import failure_detector
from datetime import datetime

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Adaptive Rollback Reality System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/status")
def get_status():
    return {
        "status": "SYSTEM ONLINE",
        "buffer_locked": ring_buffer.is_locked,
        "simulation_running": simulation_engine.is_running
    }

@app.get("/api/metrics")
def get_metrics():
    return checkpoint_controller.get_metrics()

@app.get("/api/ring-buffer")
def get_ring_buffer():
    states = ring_buffer.get_ordered_states()
    return {"states": [s.model_dump() for s in states]}

@app.post("/api/simulation/start")
async def start_simulation():
    simulation_engine.start()
    return {"status": "started"}

@app.post("/api/simulation/stop")
async def stop_simulation():
    simulation_engine.stop()
    return {"status": "stopped"}

@app.post("/api/simulation/failure")
async def force_failure():
    simulation_engine.trigger_failure()
    return {"status": "Failure demo positioned at pre-failure timestamp"}

@app.get("/api/trajectory/latest")
def get_latest_trajectory():
    if not ring_buffer.last_extracted_trajectory:
        return {"error": "No trajectory extracted yet"}
    return {
        "trajectory": [s.model_dump() for s in ring_buffer.last_extracted_trajectory],
        "root_cause": ring_buffer.last_root_cause
    }

@app.post("/api/replay/start")
def replay_start():
    if ring_buffer.last_extracted_trajectory:
        replay_engine.load_trajectory(ring_buffer.last_extracted_trajectory)
    return {"status": "ready"}

@app.post("/api/replay/step-forward")
def replay_step_forward():
    state = replay_engine.step_forward()
    return {"state": state.model_dump() if state else None}

@app.post("/api/replay/step-backward")
def replay_step_backward():
    state = replay_engine.step_backward()
    return {"state": state.model_dump() if state else None}

@app.post("/api/replay/reset")
def replay_reset():
    replay_engine.reset()
    state = replay_engine.get_current_state()
    return {"state": state.model_dump() if state else None}

@app.post("/api/iot/data")
async def receive_iot_data(payload: IoTPayload):
    psv = PhysicalStateVector(
        timestamp=payload.timestamp,
        device_id=payload.device_id,
        air_temperature=payload.temperature,
        process_temperature=payload.temperature + 10.0, # Mocked
        humidity=payload.humidity,
        vibration=payload.vibration,
        rotational_speed=payload.speed,
        torque=payload.torque,
        current=payload.current,
        tool_wear=0.0
    )

    score, status = detector.calculate_anomaly_score(psv)
    psv.anomaly_score = score

    freq, should_save = checkpoint_controller.evaluate(status)
    psv.checkpoint_level = status
    psv.machine_status = status

    is_fail, fail_details = failure_detector.evaluate(psv, score)
    if is_fail:
        psv.machine_status = "FAILURE"
        psv.is_failure = True
        ring_buffer.lock(fail_details)

    ring_buffer.append(psv)

    if should_save:
        db = SessionLocal()
        db_state = MachineStateDB(**psv.model_dump())
        db.add(db_state)
        db.commit()
        db.close()

    await manager.broadcast_state({
        "type": "state_update",
        "data": psv.model_dump(),
        "metrics": checkpoint_controller.get_metrics(),
        "buffer_locked": ring_buffer.is_locked,
        "failure_event": ring_buffer.failure_event,
        "trajectory_ready": ring_buffer.last_extracted_trajectory is not None
    })

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)

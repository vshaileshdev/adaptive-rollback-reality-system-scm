# Adaptive Rollback Reality System

This project is a prototype for an Industrial Internet-of-Things (IIoT) cyber-physical monitoring system. It acts as a "Git for physical reality" by continuously collecting state data and intelligently managing the checkpointing frequency using AI anomaly detection.

## Architecture

1.  **Frontend (React/TypeScript/Vite)**: Engineering dashboard for monitoring the machine state and running deterministic replays.
2.  **Backend (FastAPI/Python)**: Handles data streaming, anomaly detection (Isolation Forest), circular ring buffer management, trajectory extraction, and root-cause reconstruction.
3.  **IoT Firmware (ESP32/C++)**: Mock firmware template for IoT physical data transmission.

## Setup Instructions

### Backend
1. Ensure Python 3.10+ is installed.
2. Navigate to `adaptive-rollback-reality-system/`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
5. Install dependencies: `pip install -r requirements.txt`
6. Start the server: `python -m backend.main`

### Frontend
1. Ensure Node.js is installed.
2. Navigate to `adaptive-rollback-reality-system/frontend/`
3. Install dependencies: `npm install`
4. Start the development server: `npm run dev`

### Hardware (Optional)
1. Use Arduino IDE to upload `iot/esp32_node/esp32_node.ino` to an ESP32.
2. Update the `ssid` and `password` variables.
3. Update the `backendUrl` to your local machine's IP address.

## Demonstration Flow
1. Start both the Backend and Frontend servers.
2. Open the dashboard (usually `http://localhost:5173`).
3. Click **"Run Demo"**. The system will start streaming simulated data from the AI4I dataset.
4. Observe the Anomaly Score increasing as the simulated dataset approaches the failure point.
5. Notice how the **Checkpoint Frequency** increases (from every 10 states to every state) as it enters the WARNING and CRITICAL phases.
6. Once the failure occurs, the buffer locks and extracts the trajectory.
7. Enter **Replay Mode** to deterministicly step forward and backward through the failure window.
8. Review the **Root Cause Analysis** panel to see which parameters deviated first and their contribution to the failure.

## Limitations
- This is a prototype system. In a production environment, an enterprise-grade time-series database (like TimescaleDB or InfluxDB) should be used instead of SQLite.
- The Isolation Forest model is initialized with basic heuristic boundaries to fit the simulated dataset timing.

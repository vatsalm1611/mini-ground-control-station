  # Mini Ground Control Station (Mini GCS)

  A complete Ground Control Station (GCS) for drone telemetry and control, built with Python (Flask + Socket.IO) backend and React frontend.

  ## Features

  - Real-time telemetry display (position, attitude, velocity, battery)
  - Interactive map view with Mapbox GL (with fallback mode)
  - Drone controls: Arm, Disarm, Takeoff, Goto, RTL, Mode switching
  - Mission upload via JSON
  - Deterministic internal simulator (no external dependencies)
  - Optional ArduPilot SITL integration

  ## Architecture

  **Backend (Python):**
  - Flask + Flask-SocketIO server
  - Internal deterministic simulator (`TelemetrySim`)
  - Optional MAVLink client for ArduPilot SITL
  - Pydantic schema validation
  - 5Hz telemetry broadcast (configurable)

  **Frontend (React):**
  - Vite build system
  - Socket.IO client for real-time communication
  - Mapbox GL map with trajectory visualization
  - Control panel with form validation
  - Mission uploader with JSON validation

  **Communication:**
  - Socket.IO events: `telemetry`, `command`, `command_ack`, `conn_status`, `error`
  - All telemetry and commands follow strict JSON schemas

  ## Quick Start

  ### Backend (SIM Mode - Default)

  ```bash
  cd mini-gcs/backend

  # Windows (PowerShell)
  python -m venv venv
  .\venv\Scripts\Activate
  pip install -r requirements.txt

  # Linux/Mac
  bash run_local.sh

  # Set environment variables
  $env:SIM_MODE="SIM"      # Windows PowerShell
  $env:TELEMETRY_RATE="5"
  export SIM_MODE=SIM       # Linux/Mac
  export TELEMETRY_RATE=5

  # Run server
  python -m app.server
  ```

  Server will start on `http://localhost:5000`

  ### Frontend

  ```bash
  cd mini-gcs/frontend

  # Install dependencies
  npm install

  # Run dev server
  npm run dev
  ```

  Frontend will start on `http://localhost:3000`

  ## Environment Variables

  ### Backend

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `SIM_MODE` | `SIM` | `SIM` for internal simulator, `SITL` for ArduPilot |
  | `TELEMETRY_RATE` | `5` | Telemetry broadcast rate in Hz |
  | `MAVLINK_UDP_ADDR` | `127.0.0.1:14550` | MAVLink UDP address (SITL mode) |
  | `PORT` | `5000` | Backend server port |

  ### Frontend

  Create `frontend/.env.development` (already provided):

  ```
  VITE_MAPBOX_TOKEN=pk.eyJ1IjoidmF0c2FsbTE2MTEiLCJhIjoiY21oNXg2bzV4MGJvODJrczcza2FxbDNuZiJ9.SS967tO8Uzf2gPJyjDcpOQ
  VITE_BACKEND_URL=http://localhost:5000
  ```

  **Note:** The Mapbox token is public and provided for demo purposes. You can replace it with your own token.

  ## Using ArduPilot SITL (Optional)

  1. Install ArduPilot SITL:
  ```bash
  git clone https://github.com/ArduPilot/ardupilot.git
  cd ardupilot
  git submodule update --init --recursive
  ./Tools/environment_install/install-prereqs-ubuntu.sh -y  # Linux
  # Follow ArduPilot installation docs for other platforms
  ```

  2. Start SITL:
  ```bash
  cd ardupilot/ArduCopter
  sim_vehicle.py -v ArduCopter --console --map --out=127.0.0.1:14550
  ```

  3. Configure backend for SITL mode:
  ```bash
  export SIM_MODE=SITL
  export MAVLINK_UDP_ADDR=127.0.0.1:14550
  python -m app.server
  ```

  ## Running Tests

  ### Backend Tests

  ```bash
  cd mini-gcs/backend
  pytest
  ```

  Tests include:
  - Telemetry parser tests
  - Command handler tests
  - Schema validation tests
  - Simulator determinism tests

  ### Frontend Tests

  ```bash
  cd mini-gcs/frontend
  npm test
  ```

  Tests include:
  - Controls component tests
  - MapView component tests
  - Socket event handling tests

  ### Acceptance Tests

  ```bash
  cd mini-gcs
  # On Linux/Mac:
  bash acceptance_tests.sh  # legacy quick checks
  bash acceptance_controls.sh  # full flight controls E2E in SIM mode
  bash acceptance_goto_fix.sh   # verifies GOTO auto-mode-switch sequence

  # On Windows (PowerShell):
  # Run backend and frontend manually in separate terminals, then test with browser
  ```

  ## Command Schema

  All commands follow this structure:

  ```json
  {
    "id": "uuid-v4",
    "type": "command_type",
    "params": {}
  }
  ```

  ### Supported Commands

  Examples below use the command schema { id, type, params }.

  - Arm:
  ```json
  {"id": "...", "type": "arm", "params": {}}
  ```
  - Disarm (safety enforced):
  ```json
  {"id": "...", "type": "disarm", "params": {}}
  ```
  - Takeoff:
  ```json
  {"id": "...", "type": "takeoff", "params": {"alt": 10}}
  ```
  - Goto:
  ```json
  {"id": "...", "type": "goto", "params": {"lat": 26.5, "lon": 80.3, "alt": 15, "speed": 3}}
  ```
  - Hover/Stop:
  ```json
  {"id": "...", "type": "hover", "params": {"duration": 0}}
  ```
  - Set Altitude:
  ```json
  {"id": "...", "type": "set_alt", "params": {"alt": 15, "speed": 1.5}}
  ```
  - RTL (Return to Launch):
  ```json
  {"id": "...", "type": "rtl", "params": {}}
  ```
  - Upload Mission:
  ```json
  {
    "id": "...",
    "type": "upload_mission",
    "params": {
      "mission": [
        {"lat": 26.5, "lon": 80.3, "alt": 10, "command": 16},
        {"lat": 26.51, "lon": 80.31, "alt": 15, "command": 16}
      ]
    }
  }
  ```
  - Start/Pause/Continue/Abort Mission:
  ```json
  {"id": "...", "type": "start_mission", "params": {}}
  {"id": "...", "type": "pause_mission", "params": {}}
  {"id": "...", "type": "continue_mission", "params": {}}
  {"id": "...", "type": "abort_mission", "params": {}}
  ```
  - Set Mode (legacy/manual):
  ```json
  {"id": "...", "type": "set_mode", "params": {"mode": "GUIDED"}}
  ```

  ## Telemetry Schema

  Telemetry broadcasts at `TELEMETRY_RATE` Hz:

  ```json
  {
    "timestamp": "2025-10-25T06:00:00Z",
    "position": {
      "lat": 26.5,
      "lon": 80.3,
      "alt": 110.5,
      "relative_alt": 10.5
    },
    "attitude": {
      "roll": 0.0,
      "pitch": 0.0,
      "yaw": 90.0
    },
    "velocity": {
      "vx": 1.0,
      "vy": 0.0,
      "vz": 0.0,
      "speed": 1.0
    },
    "battery": {
      "voltage": 12.6,
      "current": 5.0,
      "level": 85
    },
    "mode": "GUIDED",
    "armed": true
  }
  ```

  ## API Endpoints

  **GET /health**

  Returns server status:
  ```json
  {
    "status": "ok",
    "mode": "SIM"
  }
  ```

  ## AUTO_MODE_SWITCH and GOTO behavior

  - Env var: `AUTO_MODE_SWITCH` (default: `true`).
  - When `goto` is received while vehicle mode is `HOLD`:
    - If `AUTO_MODE_SWITCH=true`, backend emits a helper `set_mode(GUIDED)` lifecycle and then executes `goto`.
    - If `AUTO_MODE_SWITCH=false`, backend rejects with: "Vehicle in HOLD — set mode to GUIDED to accept GOTO".
  - Frontend Controls also auto-switches: when you click Goto in HOLD, it emits `set_mode(GUIDED)`, waits up to 2s for mode change, then emits `goto`.

  ## Troubleshooting

  **Backend won't start:**
  - Check Python version (3.10+ required)
  - Install requirements: `pip install -r requirements.txt`
  - Check port 5000 is not in use

  **Frontend won't connect:**
  - Ensure backend is running on port 5000
  - Check VITE_BACKEND_URL in `.env.development`
  - Check browser console for errors

  **SITL connection fails:**
  - Verify SITL is running on 127.0.0.1:14550
  - Check firewall settings
  - Backend will fallback to SIM mode automatically

  **Map not showing:**
  - Check Mapbox token in `.env.development`
  - Fallback canvas mode will activate automatically

  ## Project Structure

  ```
  mini-gcs/
  ├── backend/
  │   ├── app/
  │   │   ├── __init__.py
  │   │   ├── server.py
  │   │   ├── mavlink_client.py
  │   │   ├── controllers.py
  │   │   ├── events.py
  │   │   ├── schemas.py
  │   │   └── simulator/
  │   │       └── telemetry_sim.py
  │   ├── tests/
  │   │   ├── test_parser.py
  │   │   └── test_command_handler.py
  │   ├── requirements.txt
  │   └── run_local.sh
  ├── frontend/
  │   ├── src/
  │   │   ├── components/
  │   │   │   ├── MapView.jsx
  │   │   │   ├── TelemetryPanel.jsx
  │   │   │   ├── Controls.jsx
  │   │   │   └── MissionUploader.jsx
  │   │   ├── test/
  │   │   │   ├── Controls.test.jsx
  │   │   │   └── MapView.test.jsx
  │   │   ├── App.jsx
  │   │   ├── socket.js
  │   │   └── main.jsx
  │   ├── package.json
  │   ├── vite.config.js
  │   ├── .env.development
  │   └── .env.example
  ├── README.md
  ├── ARCHITECTURE.md
  └── acceptance_tests.sh
  ```

  ## License

  MIT License - Free to use for educational and commercial purposes.

  ## Support

  For issues or questions:
  1. Check this README
  2. Review ARCHITECTURE.md for data flow details
  3. Check browser console and server logs
  4. Verify all environment variables are set correctly

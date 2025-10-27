# Mini Ground Control Station (Mini GCS)

A local, full-stack Ground Control Station for drone telemetry and control. Backend: Python (Flask + Socket.IO). Frontend: React (Vite). Ships with a deterministic simulator (SIM) and optional ArduPilot SITL support.

## Features

- Real-time telemetry (position, attitude, velocity, battery) at ~5 Hz
- Map view (Mapbox GL) with trajectory and a no-token fallback canvas
- Controls: Arm, Disarm (safety), Takeoff, Goto, Set Mode, RTL
- Mission upload (JSON waypoints)
- Deterministic internal simulator (no external deps required)
- Optional ArduPilot SITL integration (UDP 127.0.0.1:14550)
- Toast notifications on command acknowledgments

## Architecture (high level)

Backend (Python):
- Flask + Flask-SocketIO server
- Internal simulator: TelemetrySim (seedable, battery drain, simple kinematics)
- Optional MAVLink (SITL) client (pymavlink)
- Pydantic schemas for validation
- `/health` endpoint for readiness

Frontend (React):
- Vite, socket.io-client wrapper, functional components + PropTypes
- Mapbox GL + fallback canvas; telemetry panel; controls; mission uploader
- Vitest + RTL tests for Controls and MapView

Socket events:
- Client → Server: `command`
- Server → Client: `telemetry`, `command_ack`, `conn_status`, `error`

## Quick Start

### Backend (SIM mode – default)

```powershell
cd mini-gcs/backend

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux/Mac
bash run_local.sh

# Env
$env:SIM_MODE="SIM"      # Windows PowerShell
$env:TELEMETRY_RATE="5"
export SIM_MODE=SIM       # Linux/Mac
export TELEMETRY_RATE=5

# Run
python -m app.server
```

Server: http://localhost:5000

### Frontend

```bash
cd mini-gcs/frontend
npm install
npm run dev
```

App: http://localhost:3000

## Configuration

Backend env:
- `SIM_MODE` — `SIM` (default) or `SITL`
- `TELEMETRY_RATE` — Hz (default 5)
- `MAVLINK_UDP_ADDR` — UDP address for SITL (default `127.0.0.1:14550`)
- `PORT` — backend port (default 5000)

Frontend env (frontend/.env.development provided):
```env
VITE_MAPBOX_TOKEN=pk.eyJ1IjoidmF0c2FsbTE2MTEiLCJhIjoiY21oNXg2bzV4MGJvODJrczcza2FxbDNuZiJ9.SS967tO8Uzf2gPJyjDcpOQ
VITE_BACKEND_URL=http://localhost:5000
```

Note: You may replace the Mapbox token with your own.

## Using ArduPilot SITL (optional)

Recommended on Windows: WSL2 (Ubuntu).

1) Install SITL (in WSL/Linux):
```bash
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
./Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
```

2) Start SITL:
```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map --out=127.0.0.1:14550
```

3) Backend → SITL mode (Windows PowerShell with venv active):
```powershell
$env:SIM_MODE="SITL"
$env:MAVLINK_UDP_ADDR="127.0.0.1:14550"
python -m app.server
```

Open the frontend; header should show Mode: SITL.

## Commands (client → server)

All commands:
```json
{ "id": "uuid-v4", "type": "command_type", "params": {} }
```

Supported examples:
```json
{"id": "...", "type": "arm", "params": {}}
{"id": "...", "type": "disarm", "params": {}}
{"id": "...", "type": "takeoff", "params": {"alt": 10}}
{"id": "...", "type": "goto", "params": {"lat": 26.5, "lon": 80.3, "alt": 15}}
{"id": "...", "type": "set_mode", "params": {"mode": "GUIDED"}}
{"id": "...", "type": "upload_mission", "params": {"mission": [{"lat": 26.5, "lon": 80.3, "alt": 10, "command": 16}]}}
{"id": "...", "type": "rtl", "params": {}}
{"id": "...", "type": "pause", "params": {}}
{"id": "...", "type": "continue", "params": {}}
```

## Telemetry (server → client)

Shape (at ~5 Hz):
```json
{
  "timestamp": "ISO8601",
  "position": { "lat": 26.5, "lon": 80.3, "alt": 110.5, "relative_alt": 10.5 },
  "attitude": { "roll": 0.0, "pitch": 0.0, "yaw": 90.0 },
  "velocity": { "vx": 1.0, "vy": 0.0, "vz": 0.0, "speed": 1.0 },
  "battery": { "voltage": 12.6, "current": 5.0, "level": 85 },
  "mode": "GUIDED",
  "armed": true
}
```

Health endpoint:
```http
GET /health → { "status": "ok", "mode": "SIM|SITL" }
```

## Testing

Backend:
```bash
cd mini-gcs/backend
pytest
```

Frontend:
```bash
cd mini-gcs/frontend
npm test
```

Acceptance (Linux/Mac):
```bash
cd mini-gcs
bash acceptance_tests.sh
```

## Troubleshooting

- Backend won’t start: Python 3.10+, `pip install -r requirements.txt`, port 5000 free
- Frontend won’t connect: backend up? `VITE_BACKEND_URL` correct? Browser console?
- SITL fails: ensure `127.0.0.1:14550`, allow firewall, backend will fallback to SIM
- Map not showing: check Mapbox token; fallback canvas will activate automatically

## Project Structure

```text
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

MIT License

## Support

- Check this README
- See ARCHITECTURE.md
- Browser console and backend logs
- Verify env variables

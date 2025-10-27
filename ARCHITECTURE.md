# Mini GCS Architecture

This document explains the data flow and design decisions for the Mini Ground Control Station.

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          Frontend (React)                        │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────────┐│
│  │  MapView   │  │ Telemetry   │  │ Controls │  │   Mission   ││
│  │ (Mapbox GL)│  │   Panel     │  │          │  │  Uploader   ││
│  └────────────┘  └─────────────┘  └──────────┘  └─────────────┘│
│         │                │               │               │       │
│         └────────────────┴───────────────┴───────────────┘       │
│                          │                                       │
│                   ┌──────▼────────┐                             │
│                   │ Socket.IO     │                             │
│                   │ Client        │                             │
│                   └──────┬────────┘                             │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                    Socket.IO Protocol
                    (WebSocket/Polling)
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                   ┌──────▼────────┐                             │
│                   │ Flask-SocketIO│                             │
│                   │   Server      │                             │
│                   └──────┬────────┘                             │
│         ┌────────────────┼───────────────────┐                  │
│         │                │                   │                  │
│  ┌──────▼───────┐  ┌────▼─────┐  ┌─────────▼────────┐          │
│  │  Events.py   │  │Controllers│  │Telemetry Broadcast│          │
│  │              │  │           │  │    Thread (5Hz)   │          │
│  └──────┬───────┘  └────┬─────┘  └─────────┬────────┘          │
│         │               │                   │                   │
│         └───────────────┴───────────────────┘                   │
│                          │                                       │
│              ┌───────────▼──────────┐                           │
│              │   Vehicle Client     │                           │
│              │ (SIM or SITL)        │                           │
│              └───────────┬──────────┘                           │
│                          │                                       │
│         ┌────────────────┴─────────────────┐                    │
│         │                                  │                    │
│  ┌──────▼─────────┐             ┌─────────▼────────┐           │
│  │ TelemetrySim   │             │ MAVLinkClient    │           │
│  │ (Deterministic │             │ (ArduPilot SITL) │           │
│  │   Simulator)   │             │                  │           │
│  └────────────────┘             └───────┬──────────┘           │
│                                          │                      │
└──────────────────────────────────────────┼──────────────────────┘
                                           │
                                  ┌────────▼───────┐
                                  │ ArduPilot SITL │
                                  │  (UDP:14550)   │
                                  └────────────────┘
```

## Data Flow

### 1. Startup Sequence

1. **Backend Initialization:**
   - Server reads `SIM_MODE` environment variable
   - Initializes either `TelemetrySim` (default) or `MAVLinkClient`
   - Creates command controller
   - Registers Socket.IO event handlers
   - Starts telemetry broadcast thread

2. **Frontend Initialization:**
   - Loads React application
   - Creates Socket.IO client connection to `localhost:5000`
   - Registers event listeners for `telemetry`, `command_ack`, `conn_status`, `error`

3. **Connection Establishment:**
   - Socket.IO handshake
   - Server emits `conn_status` with mode (SIM/SITL) and timestamp
   - Telemetry broadcast begins at configured rate

### 2. Telemetry Flow (Server → Client)

```
┌─────────────────┐
│ Vehicle Client  │ (SIM or SITL)
│  (update loop)  │
└────────┬────────┘
         │ get_telemetry() called at TELEMETRY_RATE
         │
┌────────▼────────┐
│ Telemetry       │
│ Broadcast Thread│
└────────┬────────┘
         │ socketio.emit('telemetry', data)
         │
┌────────▼────────┐
│ Socket.IO       │
│  Transport      │
└────────┬────────┘
         │ WebSocket or HTTP Polling
         │
┌────────▼────────┐
│ Frontend        │
│ socket.on()     │
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    │          │          │          │
┌───▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
│MapView│ │Telemetry│ │Controls│ │ Footer │
└───────┘ │ Panel  │ │        │ │        │
          └────────┘ └────────┘ └────────┘
```

**Frequency:** 5Hz (configurable via `TELEMETRY_RATE`)

**Payload:** Complete telemetry object (position, attitude, velocity, battery, mode, armed)

### 3. Command Flow (Client → Server)

```
┌─────────────────┐
│ Controls        │ User clicks "Takeoff" button
│ Component       │
└────────┬────────┘
         │ onSendCommand({ id: uuid, type: 'takeoff', params: {alt: 10} })
         │
┌────────▼────────┐
│ App.jsx         │ handleSendCommand()
└────────┬────────┘
         │ socketClient.emit('command', data)
         │
┌────────▼────────┐
│ Socket.IO       │
│ Transport       │
└────────┬────────┘
         │
┌────────▼────────┐
│ Backend         │
│ events.py       │ @socketio.on('command')
└────────┬────────┘
         │ handle_command(data)
         │
┌────────▼────────┐
│ controllers.py  │ process_command()
│                 │ - Validates schema
│                 │ - Checks idempotency
│                 │ - Validates parameters
└────────┬────────┘
         │ vehicle_client.send_command()
         │
┌────────▼────────┐
│ Vehicle Client  │ (SIM or SITL)
│                 │ - Executes command
│                 │ - Updates internal state
└────────┬────────┘
         │ Returns CommandAck
         │
┌────────▼────────┐
│ Backend         │
│ events.py       │ emit('command_ack', ack)
└────────┬────────┘
         │
┌────────▼────────┐
│ Frontend        │ socket.on('command_ack')
│ App.jsx         │
└────────┬────────┘
         │
┌────────▼────────┐
│ Command Acks    │ Display in footer
│ Footer          │
└─────────────────┘
```

### 4. Command State Machine

Commands transition through states:

```
[Client Sends]
     │
     ▼
[accepted] ─────────┐
     │              │
     ▼              ▼
[executing] ──► [rejected]
     │              ▲
     ▼              │
[completed]        [failed]
```

- **accepted:** Server received and validated
- **executing:** Command in progress (e.g., climbing to altitude)
- **completed:** Command finished successfully
- **rejected:** Validation failed or precondition not met
- **failed:** Runtime error during execution

## Component Responsibilities

### Backend

**app/server.py:**
- Flask application entrypoint
- Socket.IO server setup
- Telemetry broadcast thread management
- Environment configuration

**app/events.py:**
- Socket.IO event handler registration
- Handles `connect`, `disconnect`, `command` events
- Emits `command_ack` responses

**app/controllers.py:**
- Command validation using Pydantic schemas
- Idempotency checking (duplicate command ID detection)
- Parameter validation per command type
- Delegates to vehicle client

**app/schemas.py:**
- Pydantic models for all data structures
- Ensures type safety and validation
- Documents data contracts

**app/mavlink_client.py:**
- Connects to MAVLink UDP endpoint
- Parses MAVLink messages (HEARTBEAT, GLOBAL_POSITION_INT, ATTITUDE, etc.)
- Sends MAVLink commands
- Reconnection logic

**app/simulator/telemetry_sim.py:**
- Deterministic internal simulator
- Physics simulation (climb rate, ground speed, battery drain)
- Command execution (arm, takeoff, goto, mission following)
- Seedable for reproducible tests

### Frontend

**App.jsx:**
- Root component
- Socket.IO connection management
- State management (telemetry, connectionStatus, commandAcks)
- Event handler registration
- Layout composition

**socket.js:**
- Socket.IO client wrapper
- Singleton pattern for connection sharing
- Reconnection handling
- Event emitter interface

**Components/MapView.jsx:**
- Mapbox GL integration
- Drone marker visualization
- Trajectory polyline
- Fallback canvas mode (when Mapbox token missing)

**Components/TelemetryPanel.jsx:**
- Real-time telemetry display
- Formatted position, attitude, velocity, battery
- Color-coded status indicators

**Components/Controls.jsx:**
- Command input forms
- Validation (altitude ranges, lat/lon bounds)
- UUID generation
- Command emission

**Components/MissionUploader.jsx:**
- JSON mission validation
- Sample mission loader
- Mission format help text

## Schema Contracts

### Telemetry (Server → Client)

See README.md for full schema. Key points:
- ISO8601 timestamps
- Angles in degrees
- Distances in meters
- Speeds in m/s
- Battery level as percentage (0-100)

### Commands (Client → Server)

All commands require:
- `id`: UUID v4 (idempotency key)
- `type`: One of predefined command types
- `params`: Command-specific parameters

### Command Acknowledgments (Server → Client)

- `id`: Matches command ID
- `status`: One of 5 states
- `reason`: Optional error description

## Error Handling

### Backend

1. **Validation Errors:** Pydantic raises ValidationError, caught by controller, returns `rejected` ack
2. **Duplicate Commands:** Checked in controller, returns `rejected` ack
3. **Runtime Errors:** Try-catch in send_command, returns `failed` ack
4. **SITL Connection Loss:** MAVLinkClient detects, can fallback to SIM mode

### Frontend

1. **Socket Disconnect:** Automatic reconnection with exponential backoff
2. **Command Timeout:** No built-in timeout (server responsible for ack)
3. **Invalid Input:** Form validation prevents submission
4. **Mapbox Load Failure:** Graceful fallback to canvas mode

## Performance Considerations

### Telemetry Broadcast

- Default 5Hz balances responsiveness vs bandwidth
- Uses threading to avoid blocking request handlers
- Emits to all connected clients (broadcast)

### Command Processing

- Async command handling (doesn't block telemetry)
- Idempotency prevents duplicate execution
- Command completion detection runs in simulation update loop

### Frontend Rendering

- React batches updates
- Telemetry updates trigger map re-center with easing
- Trajectory limited to last 100 points

## Extensibility

### Adding New Commands

1. Add command type to `Command` Literal in `schemas.py`
2. Create parameter schema (e.g., `NewCommandParams`)
3. Add validation in `controllers._validate_params()`
4. Implement in `TelemetrySim.send_command()` and `MAVLinkClient.send_command()`
5. Add UI controls in `Controls.jsx`

### Adding New Telemetry Fields

1. Update `TelemetryData` schema in `schemas.py`
2. Update `get_telemetry()` in simulator/client
3. Update `TelemetryPanel.jsx` to display

### Adding New Modes

1. Add to mode list in `MAVLinkClient._get_mode_id()` (for SITL)
2. Add to mode dropdown in `Controls.jsx`

## Testing Strategy

### Unit Tests (Backend)

- Schema validation tests
- Command processing tests
- Simulator physics tests
- Determinism tests (same seed → same output)

### Component Tests (Frontend)

- Controls emit correct commands
- Telemetry updates map marker
- Form validation works

### Integration Tests (Acceptance)

- End-to-end: Send command → Receive ack → Telemetry changes
- Validates full data flow through system

## Security Considerations

**Current Implementation:**
- No authentication (local development only)
- Public Mapbox token (read-only, rate-limited)
- CORS enabled for all origins

**Production Recommendations:**
- Add JWT or session-based auth
- Restrict CORS to known origins
- Rate limit commands
- Use private Mapbox token
- TLS/HTTPS
- Input sanitization (already handled by Pydantic)

## Deployment Notes

**Backend:**
- Runs as single process with threading
- Requires Python 3.10+
- pymavlink optional (only needed for SITL)

**Frontend:**
- Static assets after `npm run build`
- Can be served by any web server
- Requires backend accessible at `VITE_BACKEND_URL`

**Scaling:**
- Current design: 1 backend instance, multiple clients
- Socket.IO sticky sessions required for horizontal scaling
- Consider Redis adapter for multi-instance setups

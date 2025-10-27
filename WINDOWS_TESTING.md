# Windows Testing Guide for Mini GCS

Since the acceptance_tests.sh script is for Linux/Mac, here's how to test on Windows.

## Prerequisites

1. **Python 3.10+** installed
2. **Node.js 16+** installed
3. **PowerShell** (comes with Windows)

## Step 1: Setup Backend

```powershell
# Navigate to backend
cd C:\Users\DELL\mini-gcs\backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Run Backend Tests

```powershell
# In backend directory with venv activated
pytest

# Expected output: All tests should pass
```

## Step 3: Start Backend Server

```powershell
# Set environment variables
$env:SIM_MODE="SIM"
$env:TELEMETRY_RATE="5"

# Start server
python -m app.server

# Expected output:
# - "Starting server on port 5000"
# - "Starting telemetry broadcast at 5 Hz"
# - Server should be running without errors
```

## Step 4: Test Backend Health Endpoint

Open a NEW PowerShell window and run:

```powershell
# Test health endpoint
curl http://localhost:5000/health

# Expected output:
# {"status":"ok","mode":"SIM"}
```

## Step 5: Setup Frontend

In a NEW PowerShell window:

```powershell
# Navigate to frontend
cd C:\Users\DELL\mini-gcs\frontend

# Install dependencies
npm install

# Expected: No errors, all dependencies installed
```

## Step 6: Run Frontend Tests

```powershell
# In frontend directory
npm test

# Expected output: All tests should pass
```

## Step 7: Start Frontend

```powershell
# In frontend directory
npm run dev

# Expected output:
# - Vite dev server starts
# - Shows "Local: http://localhost:3000"
# - No build errors
```

## Step 8: Manual Acceptance Tests

Open your browser and go to `http://localhost:3000`

### Test 1: Connection and Telemetry

**Expected Results:**
- [ ] Page loads with "Mini Ground Control Station" header
- [ ] Status indicator shows "● Connected" in green
- [ ] Mode indicator shows "Mode: SIM"
- [ ] Telemetry panel shows live data updating ~5 times/second
- [ ] Map or fallback canvas is visible
- [ ] Battery shows 100%, Armed shows NO

### Test 2: Arm Command

**Actions:**
1. Click the "Arm" button

**Expected Results:**
- [ ] Command acknowledgment appears in footer: "COMPLETED - ID: 550e84..."
- [ ] Telemetry panel shows Armed: YES (in green)
- [ ] Arm button becomes disabled
- [ ] Disarm button becomes enabled

### Test 3: Takeoff Command

**Actions:**
1. Ensure drone is armed
2. Leave altitude at 10m (default)
3. Click "Takeoff" button

**Expected Results:**
- [ ] Command ack shows "EXECUTING"
- [ ] Altitude (AGL) starts increasing from 0m
- [ ] After ~5 seconds, altitude reaches ~10m
- [ ] VZ (vertical velocity) shows negative value while climbing
- [ ] Command ack updates to "COMPLETED"
- [ ] Mode changes to "GUIDED"

### Test 4: Goto Command

**Actions:**
1. Ensure drone is armed and at altitude
2. Set Goto coordinates:
   - Latitude: 26.51
   - Longitude: 80.31
   - Altitude: 15m
3. Click "Goto" button

**Expected Results:**
- [ ] Command ack shows "EXECUTING"
- [ ] Lat/Lon values start changing toward target
- [ ] Speed shows movement (~5 m/s)
- [ ] Yaw (heading) points toward target
- [ ] Map shows drone moving (if Mapbox working) or trajectory in fallback
- [ ] When reached, command ack shows "COMPLETED"

### Test 5: Mission Upload

**Actions:**
1. In Mission Uploader section, click "Load Sample Mission"
2. Click "Upload Mission" button
3. In Controls, change mode to "AUTO"

**Expected Results:**
- [ ] Alert shows "Mission uploaded successfully!"
- [ ] Command ack shows "COMPLETED" for upload_mission
- [ ] When mode set to AUTO, drone starts following waypoints
- [ ] Drone visits each waypoint in sequence

### Test 6: Battery Drain

**Actions:**
1. Let the system run for 30-60 seconds while armed

**Expected Results:**
- [ ] Battery level decreases over time
- [ ] Battery percentage goes from 100% toward lower values
- [ ] Voltage decreases proportionally
- [ ] Battery indicator changes color (green → yellow → red) as it drains

### Test 7: Disarm

**Actions:**
1. Ensure drone is on ground (altitude < 1m)
2. Click "Disarm" button

**Expected Results:**
- [ ] Command ack shows "COMPLETED"
- [ ] Armed status changes to NO (in red)
- [ ] Takeoff and other flight buttons become disabled

## Troubleshooting

### Backend won't start

```powershell
# Check Python version
python --version
# Should be 3.10 or higher

# Check if port 5000 is already in use
netstat -ano | findstr :5000

# If something is using port 5000, kill it or change PORT env var
$env:PORT="5001"
```

### Frontend can't connect

```powershell
# Verify backend is running
curl http://localhost:5000/health

# Check browser console (F12) for errors

# Verify .env.development exists
cat .\.env.development
```

### Map not showing

The Mapbox token is already configured in `.env.development`. If map still doesn't show:
- Check browser console for Mapbox errors
- Fallback canvas mode should activate automatically
- Verify internet connection (Mapbox requires external connection)

### Tests failing

```powershell
# Backend tests
cd backend
pytest -v  # Verbose mode to see which tests fail

# Frontend tests
cd frontend
npm test -- --reporter=verbose
```

## Success Criteria

All tests pass when:
- ✅ Backend tests pass (pytest)
- ✅ Frontend tests pass (npm test)
- ✅ Health endpoint responds correctly
- ✅ Telemetry streams at 5Hz
- ✅ All 7 manual acceptance tests complete successfully

## Next Steps

After all tests pass:
- Try SITL mode (if you have ArduPilot installed)
- Experiment with different commands
- Try creating custom missions
- Review ARCHITECTURE.md to understand the system

## Need Help?

1. Check server logs in backend terminal
2. Check browser console (F12 → Console tab)
3. Review README.md for configuration details
4. Verify all environment variables are set correctly

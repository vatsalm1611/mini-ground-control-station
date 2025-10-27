# Quick Start Guide - Mini GCS

Get the Mini GCS running in under 5 minutes!

## Prerequisites Check

```powershell
# Check Python (need 3.10+)
python --version

# Check Node.js (need 16+)
node --version

# If missing, install from:
# Python: https://www.python.org/downloads/
# Node.js: https://nodejs.org/
```

## Step 1: Backend Setup (2 minutes)

Open PowerShell and run:

```powershell
cd C:\Users\DELL\mini-gcs\backend

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Start Backend

```powershell
# Set environment (SIM mode - no external dependencies)
$env:SIM_MODE="SIM"
$env:TELEMETRY_RATE="5"

# Start server
python -m app.server
```

You should see:
```
INFO:__main__:Initializing SIM mode...
INFO:__main__:Starting telemetry broadcast at 5 Hz
INFO:__main__:Starting server on port 5000
```

**Leave this terminal open and running!**

## Step 3: Frontend Setup (2 minutes)

Open a NEW PowerShell window:

```powershell
cd C:\Users\DELL\mini-gcs\frontend

# Install dependencies
npm install
```

## Step 4: Start Frontend

```powershell
# In the same frontend terminal
npm run dev
```

You should see:
```
VITE ready in XXX ms
➜  Local:   http://localhost:3000
```

## Step 5: Open in Browser

1. Open your browser
2. Go to: **http://localhost:3000**

You should see:
- **Mini Ground Control Station** header
- **● Connected** status in green
- **Mode: SIM**
- Telemetry updating in real-time
- Map or fallback canvas

## Quick Test: Fly the Drone!

1. **Click "Arm"** button
   - Armed status should turn YES (green)

2. **Click "Takeoff"** button (leave 10m default)
   - Watch altitude increase from 0 to 10m over ~5 seconds
   - See command acks in footer

3. **Try "Goto"**:
   - Set Latitude: 26.51
   - Set Longitude: 80.31  
   - Set Altitude: 15
   - Click "Goto"
   - Watch drone move on map!

## That's It!

Your Mini GCS is now running with:
- ✅ Real-time telemetry at 5Hz
- ✅ Interactive controls
- ✅ Deterministic simulator
- ✅ Full command/control capabilities

## Next Steps

- Read **README.md** for full documentation
- Review **WINDOWS_TESTING.md** for comprehensive tests
- Check **ARCHITECTURE.md** to understand the system
- Try mission upload feature
- Experiment with different flight modes

## Troubleshooting

**Port 5000 already in use?**
```powershell
$env:PORT="5001"
# Then restart backend
```

**Frontend can't connect?**
```powershell
# Check backend is running:
curl http://localhost:5000/health
# Should return: {"status":"ok","mode":"SIM"}
```

**Tests failing?**
```powershell
# Backend tests
cd backend
pytest

# Frontend tests  
cd frontend
npm test
```

## Stop Everything

- Backend: Press `Ctrl+C` in backend terminal
- Frontend: Press `Ctrl+C` in frontend terminal

## Restart

Just run Step 2 and Step 4 again (skip installation steps).

---

**Having issues?** Check WINDOWS_TESTING.md for detailed troubleshooting.

"""
Tests for telemetry parsing and data structures.
"""
import pytest
from app.simulator.telemetry_sim import TelemetrySim
from app.schemas import TelemetryData


def test_simulator_initial_telemetry():
    """Test that simulator produces valid telemetry on initialization."""
    sim = TelemetrySim(seed=42)
    telemetry = sim.get_telemetry()
    
    # Validate schema
    telem_data = TelemetryData(**telemetry)
    
    assert telem_data.position.lat == 26.5
    assert telem_data.position.lon == 80.3
    assert telem_data.position.relative_alt == 0.0
    assert telem_data.armed is False
    assert telem_data.mode == "STABILIZE"
    assert telem_data.battery.level == 100


def test_simulator_update_telemetry():
    """Test that simulator updates telemetry correctly."""
    sim = TelemetrySim(seed=42)
    
    # Arm and takeoff
    sim.send_command("arm", {}, "test-1")
    sim.send_command("takeoff", {"alt": 10}, "test-2")
    
    # Update for 6 seconds (should reach 10m altitude at 2m/s)
    for _ in range(60):
        telemetry = sim.update(dt=0.1)
    
    telem_data = TelemetryData(**telemetry)
    
    assert telem_data.armed is True
    assert telem_data.mode == "GUIDED"
    assert telem_data.position.relative_alt >= 9.5  # Close to 10m
    assert telem_data.battery.level < 100  # Battery drained


def test_telemetry_json_fields():
    """Test all required telemetry fields are present."""
    sim = TelemetrySim()
    telemetry = sim.get_telemetry()
    
    # Check all required keys
    assert "timestamp" in telemetry
    assert "position" in telemetry
    assert "attitude" in telemetry
    assert "velocity" in telemetry
    assert "battery" in telemetry
    assert "mode" in telemetry
    assert "armed" in telemetry
    
    # Check nested position
    assert "lat" in telemetry["position"]
    assert "lon" in telemetry["position"]
    assert "alt" in telemetry["position"]
    assert "relative_alt" in telemetry["position"]
    
    # Check nested attitude
    assert "roll" in telemetry["attitude"]
    assert "pitch" in telemetry["attitude"]
    assert "yaw" in telemetry["attitude"]
    
    # Check nested velocity
    assert "vx" in telemetry["velocity"]
    assert "vy" in telemetry["velocity"]
    assert "vz" in telemetry["velocity"]
    assert "speed" in telemetry["velocity"]
    
    # Check nested battery
    assert "voltage" in telemetry["battery"]
    assert "level" in telemetry["battery"]


def test_simulator_determinism():
    """Test that simulator is deterministic with same seed."""
    sim1 = TelemetrySim(seed=42)
    sim2 = TelemetrySim(seed=42)
    
    sim1.send_command("arm", {}, "test-1")
    sim2.send_command("arm", {}, "test-1")
    
    sim1.send_command("takeoff", {"alt": 10}, "test-2")
    sim2.send_command("takeoff", {"alt": 10}, "test-2")
    
    for _ in range(10):
        telem1 = sim1.update(dt=0.1)
        telem2 = sim2.update(dt=0.1)
    
    assert telem1["position"]["relative_alt"] == telem2["position"]["relative_alt"]
    assert telem1["battery"]["level"] == telem2["battery"]["level"]

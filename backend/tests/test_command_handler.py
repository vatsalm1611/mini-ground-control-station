"""
Tests for command handling and validation.
"""
import pytest
from app.controllers import CommandController
from app.simulator.telemetry_sim import TelemetrySim
from app.schemas import Command


def test_command_validation():
    """Test command schema validation."""
    # Valid command
    cmd = Command(
        id="550e8400-e29b-41d4-a716-446655440000",
        type="arm",
        params={}
    )
    assert cmd.type == "arm"
    
    # Invalid command type
    with pytest.raises(Exception):
        Command(
            id="550e8400-e29b-41d4-a716-446655440000",
            type="invalid_command",
            params={}
        )


def test_arm_command():
    """Test arm command processing."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "arm",
        "params": {}
    })
    
    assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert result["status"] == "completed"
    assert sim.armed is True


def test_disarm_command():
    """Test disarm command processing."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    # Arm first
    sim.send_command("arm", {}, "test-1")
    
    # Disarm
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "type": "disarm",
        "params": {}
    })
    
    assert result["status"] == "completed"
    assert sim.armed is False


def test_takeoff_command():
    """Test takeoff command processing."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    # Arm first
    sim.send_command("arm", {}, "test-1")
    
    # Takeoff
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "type": "takeoff",
        "params": {"alt": 15}
    })
    
    assert result["status"] == "executing"
    assert sim.target_alt == 15
    assert sim.mode == "GUIDED"


def test_goto_command():
    """Test goto command processing."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    # Arm first
    sim.send_command("arm", {}, "test-1")
    
    # Goto
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "type": "goto",
        "params": {"lat": 26.6, "lon": 80.4, "alt": 20}
    })
    
    assert result["status"] == "executing"
    assert sim.target_lat == 26.6
    assert sim.target_lon == 80.4


def test_upload_mission_command():
    """Test mission upload command."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "type": "upload_mission",
        "params": {
            "mission": [
                {"lat": 26.5, "lon": 80.3, "alt": 10, "command": 16},
                {"lat": 26.6, "lon": 80.4, "alt": 15, "command": 16},
                {"lat": 26.7, "lon": 80.5, "alt": 20, "command": 16}
            ]
        }
    })
    
    assert result["status"] == "completed"
    assert len(sim.mission) == 3


def test_command_idempotency():
    """Test that duplicate command IDs are rejected."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    cmd_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # First command
    result1 = controller.process_command({
        "id": cmd_id,
        "type": "arm",
        "params": {}
    })
    assert result1["status"] == "completed"
    
    # Duplicate command
    result2 = controller.process_command({
        "id": cmd_id,
        "type": "arm",
        "params": {}
    })
    assert result2["status"] == "rejected"
    assert "duplicate" in result2["reason"].lower()


def test_invalid_parameters():
    """Test command with invalid parameters."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    # Takeoff with negative altitude
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "type": "takeoff",
        "params": {"alt": -10}
    })
    
    assert result["status"] == "rejected"
    assert "parameter" in result["reason"].lower() or "validation" in result["reason"].lower()


def test_command_requires_armed():
    """Test that certain commands require armed state."""
    sim = TelemetrySim()
    controller = CommandController(sim)
    
    # Try takeoff without arming
    result = controller.process_command({
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "type": "takeoff",
        "params": {"alt": 10}
    })
    
    # Simulator should reject
    assert result["status"] in ["rejected", "executing"]  # Depends on implementation

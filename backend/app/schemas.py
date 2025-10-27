"""Pydantic models for telemetry and command payload validation.

These models define the wire format used between frontend and backend and are
the single source of truth for tests and validation logic.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


class Position(BaseModel):
    """Position data."""
    lat: float = Field(..., description="Latitude in degrees")
    lon: float = Field(..., description="Longitude in degrees")
    alt: float = Field(..., description="Altitude MSL in meters")
    relative_alt: float = Field(..., description="Altitude AGL in meters")


class Attitude(BaseModel):
    """Attitude data."""
    roll: float = Field(..., description="Roll in degrees")
    pitch: float = Field(..., description="Pitch in degrees")
    yaw: float = Field(..., description="Yaw/heading in degrees")


class Velocity(BaseModel):
    """Velocity data."""
    vx: float = Field(..., description="X velocity in m/s")
    vy: float = Field(..., description="Y velocity in m/s")
    vz: float = Field(..., description="Z velocity in m/s")
    speed: float = Field(..., description="Ground speed in m/s")


class Battery(BaseModel):
    """Battery data."""
    voltage: float = Field(..., description="Battery voltage in volts")
    current: Optional[float] = Field(None, description="Battery current in amps")
    level: int = Field(..., ge=0, le=100, description="Battery level percentage")


class TelemetryData(BaseModel):
    """Complete telemetry data packet."""
    timestamp: str = Field(..., description="ISO8601 timestamp")
    position: Position
    attitude: Attitude
    velocity: Velocity
    battery: Battery
    mode: str = Field(..., description="Flight mode")
    armed: bool = Field(..., description="Armed status")


class TakeoffParams(BaseModel):
    """Parameters for takeoff command."""
    alt: float = Field(..., gt=0, description="Target altitude in meters")


class GotoParams(BaseModel):
    """Parameters for goto command."""
    lat: float = Field(..., ge=-90, le=90, description="Target latitude")
    lon: float = Field(..., ge=-180, le=180, description="Target longitude")
    alt: float = Field(..., gt=0, description="Target altitude in meters")
    speed: Optional[float] = Field(None, gt=0, description="Optional ground speed in m/s")


class SetAltParams(BaseModel):
    """Parameters for set_alt command."""
    alt: float = Field(..., gt=0, description="Target altitude in meters")
    speed: Optional[float] = Field(None, gt=0, description="Optional climb/descent speed in m/s")


class HoverParams(BaseModel):
    """Parameters for hover command."""
    duration: Optional[float] = Field(0, ge=0, description="Hover duration in seconds; 0 = hold until further command")


class SetModeParams(BaseModel):
    """Parameters for set_mode command."""
    mode: str = Field(..., description="Target flight mode")


class MissionWaypoint(BaseModel):
    """Single mission waypoint."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    alt: float = Field(..., gt=0)
    command: int = Field(16, description="MAVLink command ID, default 16 (NAV_WAYPOINT)")


class UploadMissionParams(BaseModel):
    """Parameters for upload_mission command."""
    mission: List[MissionWaypoint] = Field(..., min_length=1, description="Mission waypoints")


class Command(BaseModel):
    """Command from client."""
    id: str = Field(..., description="UUID v4 from client")
    type: Literal[
        "arm",
        "disarm",
        "takeoff",
        "goto",
        "hover",
        "set_alt",
        "rtl",
        "upload_mission",
        "start_mission",
        "pause_mission",
        "continue_mission",
        "abort_mission",
        "stop",
        # legacy UI commands maintained for compatibility
        "set_mode"
    ]
    params: dict = Field(default_factory=dict, description="Command parameters")

    @field_validator("id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that id is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("id must be a valid UUID")
        return v


class CommandAck(BaseModel):
    """Command acknowledgment to client."""
    id: str = Field(..., description="Command UUID")
    status: Literal["accepted", "rejected", "executing", "completed", "failed"]
    reason: Optional[str] = Field(None, description="Failure reason if applicable")


class ConnectionStatus(BaseModel):
    """Connection status message."""
    status: Literal["connected", "disconnected"]
    server_time: str = Field(..., description="ISO8601 timestamp")
    mode: Literal["SIM", "SITL"]


class ErrorMessage(BaseModel):
    """Error message to client."""
    code: int
    message: str

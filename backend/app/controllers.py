"""Command processing and safety checks.

This module validates incoming command payloads (via Pydantic schemas),
applies safety rules based on recent telemetry, and forwards accepted
commands to the configured vehicle client (SITL/MAVLink or `TelemetrySim`).

The controller keeps a short history of processed command IDs to provide
idempotency and protect against accidental double submission from the UI.
Access to that structure is synchronized with a Lock because Socket.IO can
invoke command handlers from different threads when using `async_mode='threading'`.
"""
from typing import Dict, Any, Optional, Tuple
from collections import deque
import threading
from app.schemas import (
    Command, TakeoffParams, GotoParams, SetModeParams,
    UploadMissionParams, CommandAck, HoverParams, SetAltParams
)
from pydantic import ValidationError
import logging


class CommandController:
    """Controller for processing commands and enforcing safety rules."""

    def __init__(self, vehicle_client, processed_history_size: int = 1000):
        """Create controller.

        Args:
            vehicle_client: object implementing `send_command(type, params, id)`.
            processed_history_size: number of command IDs to remember for idempotency.
        """
        self.vehicle_client = vehicle_client
        self.logger = logging.getLogger(__name__)
        # Idempotency: keep a deque for order and a set for fast membership checks.
        self._processed_lock = threading.Lock()
        self._processed_set = set()
        self._processed_deque = deque(maxlen=processed_history_size)

    def prepare_command(self, command_data: dict, telemetry_snapshot: Optional[dict]) -> Tuple[Optional[dict], Optional[tuple]]:
        """
        Validate and authorize a command. Returns either a rejected ack or a tuple for execution.
        
        Returns:
            (rejected_ack, exec_tuple) where exec_tuple = (command_id, command_type, validated_params)
        """
        try:
            command = Command(**command_data)
        except ValidationError as e:
            reason = self._friendly_validation_error(e)
            return ({
                "id": command_data.get("id", "unknown"),
                "status": "rejected",
                "reason": reason
            }, None)

        # Idempotency: check and reserve ID under lock to avoid races.
        with self._processed_lock:
            if command.id in self._processed_set:
                self.logger.warning("Duplicate command ID: %s", command.id)
                return ({
                    "id": command.id,
                    "status": "rejected",
                    "reason": "Duplicate command ID"
                }, None)

        # Param validation
        try:
            validated_params = self._validate_params(command.type, command.params)
        except ValidationError as e:
            return ({
                "id": command.id,
                "status": "rejected",
                "reason": self._friendly_validation_error(e)
            }, None)
        except ValueError as e:
            return ({
                "id": command.id,
                "status": "rejected",
                "reason": str(e)
            }, None)

        # Safety checks
        allowed, reason = self.command_allowed(command.type, validated_params, telemetry_snapshot)
        if not allowed:
            return ({
                "id": command.id,
                "status": "rejected",
                "reason": reason
            }, None)

        # Accept and proceed: record id under lock
        with self._processed_lock:
            self._processed_set.add(command.id)
            self._processed_deque.append(command.id)
        return (None, (command.id, command.type, validated_params))

    def process_command(self, command_data: dict) -> Dict[str, Any]:
        """
        Backwards-compatible processing: validate+safety then execute immediately.
        Returns an acknowledgment dict (may be executing/completed/rejected/failed).
        """
        # Build a permissive telemetry snapshot when not provided
        vc = self.vehicle_client
        telemetry_snapshot = {
            'armed': getattr(vc, 'armed', True),
            'position': {'relative_alt': getattr(vc, 'alt_rel', 0.0)},
            'velocity': {'speed': 0.0},
        }
        rejected, exec_tuple = self.prepare_command(command_data, telemetry_snapshot)
        if rejected:
            return rejected
        cmd_id, cmd_type, params = exec_tuple
        try:
            return self.vehicle_client.send_command(cmd_type, params, cmd_id)
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return {"id": cmd_id, "status": "failed", "reason": str(e)}

    def _friendly_validation_error(self, e: ValidationError) -> str:
        try:
            err = e.errors()[0]
            loc = ".".join([str(x) for x in err.get('loc', [])])
            msg = err.get('msg', 'Invalid parameters')
            # Custom mappings
            if 'alt' in loc and 'greater than 0' in msg:
                return "Validation error: Altitude must be > 0 m"
            if 'lat' in loc:
                return "Validation error: Latitude must be between -90 and 90"
            if 'lon' in loc:
                return "Validation error: Longitude must be between -180 and 180"
            return f"Validation error: {msg}"
        except Exception:
            return "Validation error: Invalid parameters"

    def _validate_params(self, command_type: str, params: dict) -> dict:
        """
        Validate command parameters and return validated dict.
        """
        if command_type == "takeoff":
            validated = TakeoffParams(**params)
            return validated.model_dump()

        elif command_type == "goto":
            validated = GotoParams(**params)
            return validated.model_dump()

        elif command_type == "set_mode":
            validated = SetModeParams(**params)
            return validated.model_dump()

        elif command_type == "upload_mission":
            validated = UploadMissionParams(**params)
            return validated.model_dump()

        elif command_type == "hover":
            validated = HoverParams(**params)
            return validated.model_dump()

        elif command_type == "set_alt":
            validated = SetAltParams(**params)
            return validated.model_dump()

        elif command_type in [
            "arm", "disarm", "rtl",
            "start_mission", "pause_mission", "continue_mission", "abort_mission", "stop"
        ]:
            return {}

        else:
            raise ValueError(f"Unknown command type: {command_type}")

    def command_allowed(self, command_type: str, params: dict, telemetry: Optional[dict]) -> tuple[bool, Optional[str]]:
        """Apply safety checks based on latest telemetry."""
        if telemetry is None:
            # If no telemetry yet, only allow connect-safe commands
            if command_type in ["arm", "upload_mission", "start_mission", "set_mode"]:
                return True, None
            return False, "No telemetry yet; try again"

        armed = telemetry.get('armed', False)
        pos = telemetry.get('position', {})
        vel = telemetry.get('velocity', {})
        rel_alt = pos.get('relative_alt', 0.0) or 0.0
        speed = vel.get('speed', 0.0) or 0.0

        if command_type == "disarm":
            if not armed:
                return False, "Already disarmed"
            if rel_alt > 0.5 or speed > 0.5:
                return False, "Cannot disarm while airborne. Land first."
            return True, None

        if command_type in ["takeoff", "goto", "hover", "set_alt", "rtl", "pause_mission", "continue_mission", "abort_mission", "stop"]:
            # Require arming for flight-affecting commands
            if not armed and command_type not in ["abort_mission", "stop"]:
                return False, "Not armed"

        # Additional checks
        if command_type == "takeoff":
            if params.get('alt', 0) <= 0:
                return False, "Takeoff altitude must be > 0 m"

        if command_type == "goto":
            lat = params.get('lat'); lon = params.get('lon'); alt = params.get('alt', 0)
            if not (-90 <= lat <= 90):
                return False, "Invalid waypoint: latitude must be between -90 and 90."
            if not (-180 <= lon <= 180):
                return False, "Invalid waypoint: longitude must be between -180 and 180."
            if alt <= 0:
                return False, "Goto altitude must be > 0 m"

        if command_type == "set_alt" and params.get('alt', 0) <= 0:
            return False, "Altitude must be > 0 m"

        if command_type == "upload_mission":
            mission = params.get('mission', [])
            if not mission:
                return False, "Mission must contain at least one waypoint"
            for idx, wp in enumerate(mission):
                lat, lon, alt = wp.get('lat'), wp.get('lon'), wp.get('alt')
                if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or not isinstance(alt, (int, float)):
                    return False, f"Waypoint {idx}: lat/lon/alt must be numbers"
                if not (-90 <= lat <= 90):
                    return False, f"Waypoint {idx}: latitude must be between -90 and 90."
                if not (-180 <= lon <= 180):
                    return False, f"Waypoint {idx}: longitude must be between -180 and 180."
                if alt <= 0:
                    return False, f"Waypoint {idx}: altitude must be > 0 m"

        return True, None

    def clear_processed_commands(self, max_age: int = 1000):
        """
        Clear old processed command IDs.
        
        Args:
            max_age: Maximum number of IDs to keep.
        """
        """ With deque we maintain maxlen automatically; this method is retained for
            compatibility but will rebuild the internal structures if called with a
            smaller `max_age` than the current capacity."""
        with self._processed_lock:
            if max_age <= 0:
                self._processed_deque = deque(maxlen=0)
                self._processed_set.clear()
                return
            if self._processed_deque.maxlen != max_age:
                # Rebuild deque with new maxlen preserving most recent entries.
                new_deque = deque(list(self._processed_deque)[-max_age:], maxlen=max_age)
                self._processed_deque = new_deque
                self._processed_set = set(self._processed_deque)

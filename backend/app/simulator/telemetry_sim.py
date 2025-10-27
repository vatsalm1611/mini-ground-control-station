"""Small deterministic flight simulator used for local development and tests.

This implementation models a minimal set of vehicle state and supports
command execution (arm/disarm/takeoff/goto/mission/etc.) so the frontend and
tests exercise the same control flow as SITL would provide. The simulator uses
an instance-level RNG to avoid mutating global random state used elsewhere in
the process (tests, other libraries).
"""

import math
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import random


class TelemetrySim:
    """Lightweight deterministic drone simulator.

    Notes:
    - Use `seed` for repeatable behavior in tests.
    - State variables are plain attributes used by tests and the command
      controller (`CommandController`) to perform validation and safety checks.
    - Methods are intentionally simple and synchronous to keep behavior
      deterministic for unit tests.
    """

    def __init__(self, seed: Optional[int] = None):
        """Create simulator and initialize state.

        Args:
            seed: Optional integer seed for deterministic randomness.
        """
        self.seed = seed or 42
        # Use an instance RNG so other code/tests don't get affected by seeding.
        self._rng = random.Random(self.seed)

        # State
        self.armed = False
        self.mode = "STABILIZE"
        self.lat = 26.5
        self.lon = 80.3
        self.alt_msl = 100.0  # MSL altitude
        self.alt_rel = 0.0    # Relative altitude (AGL)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.speed = 0.0
        self.battery_voltage = 12.6
        self.battery_current = 0.0
        self.battery_level = 100

        # Command execution state
        self.target_alt: Optional[float] = None
        self.target_lat: Optional[float] = None
        self.target_lon: Optional[float] = None
        self.mission: List[Dict[str, float]] = []
        self.current_waypoint_idx = 0
        self.executing_command: Optional[str] = None
        self.command_id: Optional[str] = None

        # Physics constants (can be overridden by params during execution)
        self.climb_rate = 2.0  # m/s
        self.ground_speed = 5.0  # m/s
        self.battery_drain_rate = 0.1  # % per second when armed

        self.last_update = time.time()

        # Hover timing
        self.hover_end_time: Optional[float] = None

    def update(self, dt: Optional[float] = None) -> Dict[str, Any]:
        """Advance simulation by dt seconds and return the latest telemetry dict."""
        if dt is None:
            now = time.time()
            dt = now - self.last_update
            self.last_update = now

        if self.armed:
            self._update_flight(dt)
            self._drain_battery(dt)

        return self.get_telemetry()

    def _update_flight(self, dt: float):
        """Update flight state based on current command."""
        # Execute vertical movement toward target_alt
        if self.target_alt is not None and abs(self.alt_rel - self.target_alt) > 0.05:
            direction = 1 if self.target_alt > self.alt_rel else -1
            delta = self.climb_rate * dt
            self.alt_rel += direction * delta
            self.vz = -self.climb_rate * direction  # Negative is up in NED
            # Clamp
            if (direction > 0 and self.alt_rel >= self.target_alt) or (direction < 0 and self.alt_rel <= self.target_alt):
                self.alt_rel = self.target_alt
                self.vz = 0.0
                if self.command_id and self.executing_command in ("takeoff", "set_alt"):
                    self.executing_command = None

        # Execute goto or mission waypoint
        if self.target_lat is not None and self.target_lon is not None:
            dlat = self.target_lat - self.lat
            dlon = self.target_lon - self.lon
            distance = math.sqrt(dlat**2 + dlon**2) * 111000  # rough meters

            if distance > 1.0:  # Not at waypoint yet
                bearing = math.atan2(dlon, dlat)
                move_distance = min(self.ground_speed * dt / 111000, distance / 111000)
                self.lat += math.cos(bearing) * move_distance
                self.lon += math.sin(bearing) * move_distance
                self.vx = math.cos(bearing) * self.ground_speed
                self.vy = math.sin(bearing) * self.ground_speed
                self.speed = self.ground_speed
                self.yaw = math.degrees(bearing) % 360
            else:
                # Reached waypoint
                self.lat = self.target_lat
                self.lon = self.target_lon
                self.vx = 0.0
                self.vy = 0.0
                self.speed = 0.0

                if self.executing_command == "goto":
                    self.target_lat = None
                    self.target_lon = None
                    self.executing_command = None
                elif self.mode == "AUTO" and self.mission:
                    # Dwell briefly (no timing implemented; advance immediately)
                    self.current_waypoint_idx += 1
                    if self.current_waypoint_idx < len(self.mission):
                        wp = self.mission[self.current_waypoint_idx]
                        self.target_lat = wp["lat"]
                        self.target_lon = wp["lon"]
                        self.target_alt = wp["alt"]
                    else:
                        # Mission complete
                        self.target_lat = None
                        self.target_lon = None
                        self.executing_command = None
                        self.mode = "HOLD"

        # Handle hover duration completion
        if self.executing_command == "hover" and self.hover_end_time is not None:
            if time.time() >= self.hover_end_time:
                self.hover_end_time = None
                self.executing_command = None

    def _drain_battery(self, dt: float):
        """Drain battery while armed."""
        drain = self.battery_drain_rate * dt
        self.battery_level = max(0, self.battery_level - drain)
        self.battery_voltage = 12.6 * (self.battery_level / 100.0)
        self.battery_current = 5.0 if self.speed > 0 else 2.0

    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "position": {
                "lat": self.lat,
                "lon": self.lon,
                "alt": self.alt_msl + self.alt_rel,
                "relative_alt": self.alt_rel
            },
            "attitude": {
                "roll": self.roll,
                "pitch": self.pitch,
                "yaw": self.yaw
            },
            "velocity": {
                "vx": self.vx,
                "vy": self.vy,
                "vz": self.vz,
                "speed": self.speed
            },
            "battery": {
                "voltage": round(self.battery_voltage, 2),
                "current": round(self.battery_current, 2) if self.battery_current else None,
                "level": int(self.battery_level)
            },
            "mode": self.mode,
            "armed": self.armed
        }

    def send_command(self, command_type: str, params: Dict[str, Any], command_id: str) -> Dict[str, Any]:
        """Execute a command."""
        self.command_id = command_id

        if command_type == "arm":
            if self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Already armed"}
            self.armed = True
            return {"id": command_id, "status": "completed", "reason": None}

        elif command_type == "disarm":
            if not self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Already disarmed"}
            if self.alt_rel > 0.5:
                return {"id": command_id, "status": "rejected", "reason": "Cannot disarm in air"}
            self.armed = False
            self.mode = "STABILIZE"
            return {"id": command_id, "status": "completed", "reason": None}

        elif command_type == "takeoff":
            if not self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Not armed"}
            alt = params.get("alt", 10)
            self.target_alt = alt
            self.mode = "GUIDED"
            self.executing_command = "takeoff"
            return {"id": command_id, "status": "executing", "reason": None}

        elif command_type == "goto":
            if not self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Not armed"}
            self.target_lat = params.get("lat")
            self.target_lon = params.get("lon")
            self.target_alt = params.get("alt", self.alt_rel)
            # Optional speed override
            if params.get("speed"):
                self.ground_speed = float(params["speed"]) or self.ground_speed
            self.mode = "GUIDED"
            self.executing_command = "goto"
            return {"id": command_id, "status": "executing", "reason": None}

        elif command_type == "hover":
            # Hold current position (LOITER/HOLD)
            self.target_lat = self.lat
            self.target_lon = self.lon
            duration = float(params.get("duration", 0) or 0)
            self.hover_end_time = (time.time() + duration) if duration > 0 else None
            self.mode = "HOLD"
            self.executing_command = "hover" if duration > 0 else None
            return {"id": command_id, "status": "executing" if duration > 0 else "completed", "reason": None}

        elif command_type == "set_alt":
            if not self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Not armed"}
            self.target_alt = params.get("alt", self.alt_rel)
            if params.get("speed"):
                self.climb_rate = float(params["speed"]) or self.climb_rate
            self.executing_command = "set_alt"
            self.mode = "GUIDED"
            return {"id": command_id, "status": "executing", "reason": None}

        elif command_type == "set_mode":
            mode = params.get("mode", "STABILIZE")
            self.mode = mode
            if mode.upper() == "LAND":
                # Initiate descent to ground
                self.target_alt = 0.0
                self.executing_command = "set_alt"
            return {"id": command_id, "status": "completed", "reason": None}
        
        elif command_type == "upload_mission":
            mission = params.get("mission", [])
            if not mission:
                return {"id": command_id, "status": "rejected", "reason": "Empty mission"}
            self.mission = mission
            self.current_waypoint_idx = 0
            return {"id": command_id, "status": "completed", "reason": None}
        
        elif command_type == "start_mission":
            if not self.mission:
                return {"id": command_id, "status": "rejected", "reason": "No mission uploaded"}
            self.mode = "AUTO"
            wp = self.mission[0]
            self.current_waypoint_idx = 0
            self.target_lat = wp["lat"]
            self.target_lon = wp["lon"]
            self.target_alt = wp["alt"]
            self.executing_command = "goto"
            return {"id": command_id, "status": "executing", "reason": None}

        elif command_type == "pause_mission":
            self.mode = "HOLD"
            return {"id": command_id, "status": "completed", "reason": None}

        elif command_type == "continue_mission":
            if not self.mission:
                return {"id": command_id, "status": "rejected", "reason": "No mission uploaded"}
            self.mode = "AUTO"
            # Continue toward current target (assumes target set)
            return {"id": command_id, "status": "completed", "reason": None}

        elif command_type == "abort_mission" or command_type == "stop":
            self.mode = "HOLD"
            self.target_lat = None
            self.target_lon = None
            self.executing_command = None
            return {"id": command_id, "status": "completed", "reason": None}
        
        elif command_type == "rtl":
            if not self.armed:
                return {"id": command_id, "status": "rejected", "reason": "Not armed"}
            # Return to launch - go back to starting position
            self.target_lat = 26.5
            self.target_lon = 80.3
            self.mode = "RTL"
            self.executing_command = "goto"
            return {"id": command_id, "status": "executing", "reason": None}
        
        return {"id": command_id, "status": "rejected", "reason": f"Unknown command: {command_type}"}

    def check_command_completion(self) -> Optional[Dict[str, Any]]:
        """
        Check if executing command is complete and return an ack if so.
        """
        if not self.command_id or not self.executing_command:
            return None
        
        if self.executing_command in ("takeoff", "set_alt"):
            if self.target_alt is not None and abs(self.alt_rel - self.target_alt) <= 0.1:
                cmd_id = self.command_id
                self.command_id = None
                self.executing_command = None
                return {"id": cmd_id, "status": "completed", "reason": None}
        
        elif self.executing_command == "goto":
            if self.target_lat is not None and self.target_lon is not None:
                dlat = abs(self.target_lat - self.lat)
                dlon = abs(self.target_lon - self.lon)
                if dlat < 0.0001 and dlon < 0.0001:  # Close enough
                    cmd_id = self.command_id
                    self.command_id = None
                    self.executing_command = None
                    return {"id": cmd_id, "status": "completed", "reason": None}
        
        elif self.executing_command == "hover":
            if self.hover_end_time is None:
                cmd_id = self.command_id
                self.command_id = None
                self.executing_command = None
                return {"id": cmd_id, "status": "completed", "reason": None}

        return None

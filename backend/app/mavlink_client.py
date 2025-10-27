"""MAVLink client wrapper for SITL (pymavlink).

This module wraps a `pymavlink` connection and extracts telemetry fields
needed by the rest of the app. The wrapper keeps an internal, poll-based
thread to receive MAVLink messages and update a small telemetry cache
exposed via `get_telemetry()`.
"""
from typing import Optional, Dict, Any, Callable
import threading
import time
from datetime import datetime, timezone
import logging

try:
    from pymavlink import mavutil
    PYMAVLINK_AVAILABLE = True
except ImportError:
    PYMAVLINK_AVAILABLE = False
    logging.warning('pymavlink not available, SITL mode will not work')


class MAVLinkClient:
    """MAVLink client wrapper for SITL connection."""

    def __init__(self, connection_string: str = "udp:127.0.0.1:14550"):
        """
        Initialize MAVLink client.
        
        Args:
            connection_string: MAVLink connection string.
        """
        if not PYMAVLINK_AVAILABLE:
            raise RuntimeError("pymavlink is not installed")
        
        self.connection_string = connection_string
        self.master = None
        self.connected = False
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.telemetry_callback: Optional[Callable] = None
        
        # Latest telemetry state
        self.lat = 0.0
        self.lon = 0.0
        self.alt_msl = 0.0
        self.alt_rel = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.speed = 0.0
        self.battery_voltage = 0.0
        self.battery_current = None
        self.battery_level = 0
        self.mode = "UNKNOWN"
        self.armed = False
        
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """Connect to MAVLink endpoint."""
        try:
            self.logger.info(f"Connecting to MAVLink: {self.connection_string}")
            self.master = mavutil.mavlink_connection(self.connection_string)
            
            # Wait for heartbeat
            self.logger.info("Waiting for heartbeat...")
            self.master.wait_heartbeat(timeout=10)
            self.connected = True
            self.logger.info("Connected to MAVLink")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MAVLink: {e}")
            self.connected = False
            return False

    def start(self, telemetry_callback: Optional[Callable] = None):
        """Start MAVLink message processing thread."""
        if self.running:
            return
        
        self.telemetry_callback = telemetry_callback
        self.running = True
        self.thread = threading.Thread(target=self._message_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop MAVLink message processing."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.master:
            self.master.close()
        self.connected = False

    def _message_loop(self):
        """Main message processing loop."""
        while self.running:
            if not self.connected:
                time.sleep(1)
                continue
            
            try:
                msg = self.master.recv_match(blocking=False, timeout=0.1)
                if msg:
                    self._process_message(msg)
            except Exception as e:
                self.logger.error(f"Error receiving MAVLink message: {e}")
                self.connected = False
            
            time.sleep(0.01)

    def _process_message(self, msg):
        """Process incoming MAVLink message."""
        msg_type = msg.get_type()
        
        if msg_type == "HEARTBEAT":
            self.armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
            # Get mode string
            if hasattr(msg, 'custom_mode'):
                self.mode = self._get_mode_string(msg.custom_mode)
        
        elif msg_type == "GLOBAL_POSITION_INT":
            self.lat = msg.lat / 1e7
            self.lon = msg.lon / 1e7
            self.alt_msl = msg.alt / 1000.0
            self.alt_rel = msg.relative_alt / 1000.0
            self.vx = msg.vx / 100.0
            self.vy = msg.vy / 100.0
            self.vz = msg.vz / 100.0
        
        elif msg_type == "ATTITUDE":
            self.roll = msg.roll * 57.2958  # rad to deg
            self.pitch = msg.pitch * 57.2958
            self.yaw = msg.yaw * 57.2958
            if self.yaw < 0:
                self.yaw += 360
        
        elif msg_type == "VFR_HUD":
            self.speed = msg.groundspeed
        
        elif msg_type == "SYS_STATUS":
            self.battery_voltage = msg.voltage_battery / 1000.0
            self.battery_current = msg.current_battery / 100.0 if msg.current_battery != -1 else None
            self.battery_level = msg.battery_remaining if msg.battery_remaining != -1 else 0
        
        elif msg_type == "BATTERY_STATUS":
            if hasattr(msg, 'voltages') and msg.voltages[0] != 65535:
                self.battery_voltage = msg.voltages[0] / 1000.0
            if hasattr(msg, 'current_battery') and msg.current_battery != -1:
                self.battery_current = msg.current_battery / 100.0
            if hasattr(msg, 'battery_remaining') and msg.battery_remaining != -1:
                self.battery_level = msg.battery_remaining

    def _get_mode_string(self, custom_mode: int) -> str:
        """Convert custom mode to string (ArduCopter specific)."""
        modes = {
            0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
            4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
            9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
            15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE", 18: "THROW",
            19: "AVOID_ADSB", 20: "GUIDED_NOGPS", 21: "SMART_RTL",
            22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG", 25: "SYSTEMID",
            26: "AUTOROTATE", 27: "AUTO_RTL"
        }
        return modes.get(custom_mode, f"MODE_{custom_mode}")

    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "position": {
                "lat": self.lat,
                "lon": self.lon,
                "alt": self.alt_msl,
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
        """Send command to vehicle."""
        if not self.connected or not self.master:
            return {"id": command_id, "status": "rejected", "reason": "Not connected"}
        
        try:
            if command_type == "arm":
                # Arm via command_long
                self.master.mav.command_long_send(
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    1, 0, 0, 0, 0, 0, 0
                )
                return {"id": command_id, "status": "executing", "reason": None}
            
            elif command_type == "disarm":
                self.master.mav.command_long_send(
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    0, 0, 0, 0, 0, 0, 0
                )
                return {"id": command_id, "status": "executing", "reason": None}
            
            elif command_type == "takeoff":
                alt = params.get("alt", 10)
                self.master.mav.command_long_send(
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                    0, 0, 0, 0, 0, 0, 0, alt
                )
                return {"id": command_id, "status": "executing", "reason": None}
            
            elif command_type == "goto":
                lat = params.get("lat")
                lon = params.get("lon")
                alt = params.get("alt", self.alt_rel)
                
                self.master.mav.set_position_target_global_int_send(
                    0,
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    0b0000111111111000,
                    int(lat * 1e7), int(lon * 1e7), float(alt),
                    0, 0, 0, 0, 0, 0, 0, 0
                )
                return {"id": command_id, "status": "executing", "reason": None}
            
            elif command_type == "hover":
                # Switch to LOITER to hold position
                loiter_id = self._get_mode_id("LOITER")
                if loiter_id is not None:
                    self.master.set_mode(loiter_id)
                return {"id": command_id, "status": "completed", "reason": None}

            elif command_type == "set_alt":
                # Keep current lat/lon, change altitude
                lat = self.lat
                lon = self.lon
                alt = params.get("alt", self.alt_rel)
                self.master.mav.set_position_target_global_int_send(
                    0,
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    0b0000111111111000,
                    int(lat * 1e7), int(lon * 1e7), float(alt),
                    0, 0, 0, 0, 0, 0, 0, 0
                )
                return {"id": command_id, "status": "executing", "reason": None}

            elif command_type == "set_mode":
                mode = params.get("mode", "GUIDED")
                mode_id = self._get_mode_id(mode)
                if mode_id is None:
                    return {"id": command_id, "status": "rejected", "reason": f"Unknown mode: {mode}"}
                self.master.set_mode(mode_id)
                return {"id": command_id, "status": "completed", "reason": None}
            
            elif command_type == "rtl":
                self.master.set_mode_rtl()
                return {"id": command_id, "status": "executing", "reason": None}
            
            elif command_type == "upload_mission":
                return {"id": command_id, "status": "completed", "reason": None}

            elif command_type == "start_mission":
                auto_id = self._get_mode_id("AUTO")
                if auto_id is not None:
                    self.master.set_mode(auto_id)
                return {"id": command_id, "status": "executing", "reason": None}

            elif command_type == "pause_mission":
                loiter_id = self._get_mode_id("LOITER")
                if loiter_id is not None:
                    self.master.set_mode(loiter_id)
                return {"id": command_id, "status": "completed", "reason": None}

            elif command_type == "continue_mission":
                auto_id = self._get_mode_id("AUTO")
                if auto_id is not None:
                    self.master.set_mode(auto_id)
                return {"id": command_id, "status": "completed", "reason": None}

            elif command_type in ("abort_mission", "stop"):
                guided_id = self._get_mode_id("GUIDED")
                if guided_id is not None:
                    self.master.set_mode(guided_id)
                loiter_id = self._get_mode_id("LOITER")
                if loiter_id is not None:
                    self.master.set_mode(loiter_id)
                return {"id": command_id, "status": "completed", "reason": None}
            
            else:
                return {"id": command_id, "status": "rejected", "reason": f"Unknown command: {command_type}"}
        
        except Exception as e:
            self.logger.error(f"Error sending command: {e}")
            return {"id": command_id, "status": "rejected", "reason": str(e)}

    def _get_mode_id(self, mode: str) -> Optional[int]:
        """Get mode ID from mode string."""
        modes = {
            "STABILIZE": 0, "ACRO": 1, "ALT_HOLD": 2, "AUTO": 3,
            "GUIDED": 4, "LOITER": 5, "RTL": 6, "CIRCLE": 7,
            "LAND": 9, "DRIFT": 11, "SPORT": 13, "FLIP": 14,
            "AUTOTUNE": 15, "POSHOLD": 16, "BRAKE": 17
        }
        return modes.get(mode.upper())

"""
Tests for safety validation and MAVLink mapping.
"""
import types
import pytest

from app.controllers import CommandController
from app.simulator.telemetry_sim import TelemetrySim


def test_takeoff_invalid_alt_rejected():
    sim = TelemetrySim()
    controller = CommandController(sim)
    telemetry = sim.get_telemetry()

    cmd = {"id": "550e8400-e29b-41d4-a716-446655440010", "type": "takeoff", "params": {"alt": 0}}
    rejected, exec_tuple = controller.prepare_command(cmd, telemetry)
    assert rejected is not None
    assert rejected["status"] == "rejected"
    assert "altitude" in rejected["reason"].lower()


def test_disarm_in_air_rejected():
    sim = TelemetrySim()
    controller = CommandController(sim)
    # Simulate airborne telemetry
    sim.armed = True
    sim.alt_rel = 5.0
    telemetry = sim.get_telemetry()

    cmd = {"id": "550e8400-e29b-41d4-a716-446655440011", "type": "disarm", "params": {}}
    rejected, exec_tuple = controller.prepare_command(cmd, telemetry)
    assert rejected is not None
    assert rejected["status"] == "rejected"
    assert "disarm" in rejected["reason"].lower()


def test_goto_translation_mavlink(monkeypatch):
    # Import here to allow monkeypatch of mavutil
    import app.mavlink_client as mc

    class FakeMav:
        def __init__(self):
            self.calls = []
        def set_position_target_global_int_send(self, *args):
            self.calls.append(("set_position_target_global_int_send", args))
        def command_long_send(self, *args):
            self.calls.append(("command_long_send", args))

    class FakeMaster:
        def __init__(self):
            self.mav = FakeMav()
            self.target_system = 1
            self.target_component = 1

    # Bypass pymavlink requirement and constructor
    monkeypatch.setattr(mc, 'PYMAVLINK_AVAILABLE', True)

    def fake_init(self, connection_string: str = "udp:127.0.0.1:14550"):
        self.connection_string = connection_string
        self.master = FakeMaster()
        self.connected = True
        self.lat = 26.5
        self.lon = 80.3
        self.alt_rel = 10.0
        self.logger = types.SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None)

    class FakeMavutil:
        class mavlink:
            MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 6
    monkeypatch.setattr(mc, 'mavutil', FakeMavutil, raising=False)

    monkeypatch.setattr(mc.MAVLinkClient, '__init__', fake_init)

    client = mc.MAVLinkClient("udp:127.0.0.1:14550")
    res = client.send_command('goto', {"lat": 26.6, "lon": 80.4, "alt": 20}, "cmd-1")
    assert res["status"] in ("executing", "accepted")

    # Verify call captured
    calls = client.master.mav.calls
    assert any(name == 'set_position_target_global_int_send' for name, _ in calls)
    # Inspect last call args (frame and coords)
    name, args = next((n, a) for n, a in calls if n == 'set_position_target_global_int_send')
    # args: time_boot_ms, sys, comp, frame, type_mask, lat_int, lon_int, alt, ...
    frame = args[3]
    lat_int = args[5]
    lon_int = args[6]
    alt = args[7]
    assert frame == getattr(mc.mavutil.mavlink, 'MAV_FRAME_GLOBAL_RELATIVE_ALT_INT', 6)
    assert isinstance(lat_int, int) and isinstance(lon_int, int)
    assert alt == pytest.approx(20.0)

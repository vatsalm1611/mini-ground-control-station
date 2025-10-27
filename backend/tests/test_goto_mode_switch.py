"""
Test AUTO_MODE_SWITCH: goto in HOLD triggers internal set_mode then goto.
"""
import os
import uuid
import types
import pytest

from app.controllers import CommandController
from app.simulator.telemetry_sim import TelemetrySim
import sys
import types as _types
mod = _types.ModuleType('flask_socketio')
setattr(mod, 'emit', lambda *a, **k: None)
sys.modules['flask_socketio'] = mod
from app.events import register_socketio_events


class FakeSocketIO:
    def __init__(self):
        self.handlers = {}
        self.emitted = []

    def on(self, evt):
        def deco(fn):
            self.handlers[evt] = fn
            return fn
        return deco

    def emit(self, evt, payload=None):
        self.emitted.append((evt, payload))


def test_goto_mode_switch_sequence(monkeypatch):
    # Force AUTO_MODE_SWITCH true
    auto = True

    # Vehicle client using simulator
    sim = TelemetrySim()
    sim.armed = True
    controller = CommandController(sim)

    # Telemetry snapshot starts in HOLD
    sim.mode = "HOLD"

    sio = FakeSocketIO()
    register_socketio_events(sio, controller, get_telemetry_fn=lambda: sim.get_telemetry(), auto_mode_switch=auto)

    # Build goto command
    gid = str(uuid.uuid4())
    goto_cmd = {"id": gid, "type": "goto", "params": {"lat": 26.6, "lon": 80.4, "alt": 10}}

    # Invoke command handler
    assert 'command' in sio.handlers
    sio.handlers['command'](goto_cmd)

    # Extract command_ack payloads
    acks = [p for (evt, p) in sio.emitted if evt == 'command_ack']

    # Expect first an accepted for helper set_mode, then completed for helper, then accepted for goto, etc.
    assert any(ack['status'] == 'accepted' for ack in acks), "No accepted ack emitted"

    # Find the helper set_mode accepted ack (ID != gid)
    helper_ids = [ack['id'] for ack in acks if ack['id'] != gid]
    assert helper_ids, "No helper set_mode ack id found"

    # Ensure goto accepted present
    assert any(ack['id'] == gid and ack['status'] == 'accepted' for ack in acks)

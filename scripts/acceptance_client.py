# Acceptance client driving Mini GCS via Socket.IO
import sys
import time
import json
import math

import socketio

BACKEND_URL = 'http://localhost:5000'

sio = socketio.Client()
telemetry = None
acks = {}

@sio.event
def connect():
    print('Connected')

@sio.on('telemetry')
def on_telem(data):
    global telemetry
    telemetry = data

@sio.on('command_ack')
def on_ack(data):
    acks[data['id']] = data


def wait_for(predicate, timeout=10.0, interval=0.1, desc='condition'):
    start = time.time()
    while time.time() - start < timeout:
        if predicate():
            return True
        time.sleep(interval)
    raise RuntimeError(f'Timeout waiting for {desc}')


def send_command(cmd_type, params=None):
    import uuid
    cid = str(uuid.uuid4())
    payload = {"id": cid, "type": cmd_type, "params": params or {}}
    sio.emit('command', payload)
    return cid


def expect_rejected(cid):
    wait_for(lambda: cid in acks and acks[cid]['status'] in ('rejected','failed'), desc='rejected ack')
    status = acks[cid]['status']
    assert status == 'rejected', f'Expected rejected, got {status}'


def expect_completed(cid, timeout=15.0):
    wait_for(lambda: cid in acks and acks[cid]['status'] in ('completed','failed','rejected'), timeout=timeout, desc='completed ack')
    status = acks[cid]['status']
    assert status == 'completed', f'Expected completed, got {status} ({acks[cid].get("reason")})'


def main():
    sio.connect(BACKEND_URL, transports=['websocket','polling'])
    wait_for(lambda: telemetry is not None, desc='initial telemetry')

    # Invalid takeoff
    cid = send_command('takeoff', {"alt": 0})
    expect_rejected(cid)

    # Arm
    cid = send_command('arm')
    expect_completed(cid)

    # Takeoff to 10m
    start_alt = telemetry['position']['relative_alt']
    cid = send_command('takeoff', {"alt": 10})
    # Wait for altitude rise
    wait_for(lambda: telemetry['position']['relative_alt'] > start_alt + 2, timeout=8.0, desc='altitude rising')
    expect_completed(cid)

    # Goto new position
    start_lat, start_lon = telemetry['position']['lat'], telemetry['position']['lon']
    target = {"lat": start_lat + 0.01, "lon": start_lon + 0.01, "alt": 10}
    cid = send_command('goto', target)
    wait_for(lambda: abs(telemetry['position']['lat'] - start_lat) > 0.005, timeout=15.0, desc='position moved')
    expect_completed(cid)

    # Hover
    cid = send_command('hover', {"duration": 1})
    # wait briefly and ensure speed near 0
    time.sleep(1.5)
    assert abs(telemetry['velocity']['speed']) <= 5.0  # simulator caps to 0 quickly
    expect_completed(cid)

    # Set altitude
    cid = send_command('set_alt', {"alt": 12})
    wait_for(lambda: math.isclose(telemetry['position']['relative_alt'], 12, abs_tol=0.5), timeout=10.0, desc='altitude to 12')
    expect_completed(cid)

    # Mission upload and start
    mission = [
        {"lat": telemetry['position']['lat'], "lon": telemetry['position']['lon'], "alt": 12, "command": 16},
        {"lat": telemetry['position']['lat'] + 0.005, "lon": telemetry['position']['lon'] + 0.005, "alt": 12, "command": 16},
    ]
    cid = send_command('upload_mission', {"mission": mission})
    expect_completed(cid)

    cid = send_command('start_mission')
    # Wait for movement
    wait_for(lambda: abs(telemetry['position']['lat'] - mission[-1]['lat']) < 0.001 and abs(telemetry['position']['lon'] - mission[-1]['lon']) < 0.001, timeout=25.0, desc='mission reach last wp')
    # Pause/continue/abort quick checks
    cidp = send_command('pause_mission')
    expect_completed(cidp)
    cidc = send_command('continue_mission')
    expect_completed(cidc)
    cida = send_command('abort_mission')
    expect_completed(cida)

    sio.disconnect()
    print('ACCEPTANCE OK')

if __name__ == '__main__':
    main()

# Acceptance client for GOTO auto-mode-switch
import time
import uuid
import socketio

BACKEND_URL = 'http://localhost:5000'

sio = socketio.Client()
acks = []
telemetry = None

@sio.on('telemetry')
def on_t(data):
    global telemetry
    telemetry = data

@sio.on('command_ack')
def on_ack(a):
    acks.append(a)


def wait_for(pred, timeout=5.0, interval=0.05):
    start = time.time()
    while time.time() - start < timeout:
        if pred():
            return True
        time.sleep(interval)
    raise RuntimeError('timeout')


def main():
    sio.connect(BACKEND_URL, transports=['websocket','polling'])
    wait_for(lambda: telemetry is not None, 5.0)

    # Ensure HOLD mode
    # If not HOLD, send hover to force HOLD
    if telemetry.get('mode') != 'HOLD':
        cid = str(uuid.uuid4())
        sio.emit('command', { 'id': cid, 'type': 'hover', 'params': { 'duration': 0 } })
        time.sleep(0.5)

    # Send goto while HOLD
    gid = str(uuid.uuid4())
    lat = telemetry['position']['lat'] + 0.002
    lon = telemetry['position']['lon'] + 0.002
    sio.emit('command', { 'id': gid, 'type': 'goto', 'params': { 'lat': lat, 'lon': lon, 'alt': max(5, telemetry['position']['relative_alt'] or 5) } })

    # Expect acks sequence: helper set_mode accepted -> goto accepted -> goto executing -> goto completed
    wait_for(lambda: len(acks) >= 2, 3.0)
    assert any(a['status']=='accepted' and a['id']!=gid for a in acks), 'no helper set_mode accepted'
    wait_for(lambda: any(a['id']==gid and a['status'] in ('executing','completed') for a in acks), 10.0)
    wait_for(lambda: any(a['id']==gid and a['status']=='completed' for a in acks), 20.0)
    print('ACCEPTANCE_GOTO_OK')
    sio.disconnect()

if __name__ == '__main__':
    main()

"""
Main Flask server with Socket.IO for Mini GCS.
"""
import os
import sys
import logging
import threading
import time
from datetime import datetime, timezone
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from app.simulator.telemetry_sim import TelemetrySim
from app.controllers import CommandController
from app.events import register_socketio_events

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
# Default to SIM; you can switch to SITL by setting SIM_MODE=SITL
SIM_MODE = os.getenv('SIM_MODE', 'SIM')  # SIM or SITL
TELEMETRY_RATE = int(os.getenv('TELEMETRY_RATE', '5'))  # Hz
MAVLINK_UDP_ADDR = os.getenv('MAVLINK_UDP_ADDR', '127.0.0.1:14550')
PORT = int(os.getenv('PORT', '5000'))
AUTO_MODE_SWITCH = os.getenv('AUTO_MODE_SWITCH', 'true').lower() in ('1','true','yes')

# Create Flask app
app = Flask(__name__)
# Prefer reading secret from environment for production; fallback only for
# development/test convenience.
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mini-gcs-dev-secret')
CORS(app)

# Create Socket.IO instance (threading mode used for simple local runs/tests).
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
latest_telemetry = {}
vehicle_client = None
command_controller = None
telemetry_thread = None
# Use an Event for clean shutdown signaling to background threads.
telemetry_stop_event = threading.Event()


def initialize_vehicle_client():
    """Initialize vehicle client based on SIM_MODE."""
    global vehicle_client
    
    if SIM_MODE == 'SITL':
        logger.info("Initializing SITL mode...")
        try:
            from app.mavlink_client import MAVLinkClient
            vehicle_client = MAVLinkClient(f"udp:{MAVLINK_UDP_ADDR}")
            if vehicle_client.connect():
                vehicle_client.start()
                logger.info("SITL client connected")
            else:
                logger.warning("SITL connection failed, falling back to SIM mode")
                vehicle_client = TelemetrySim()
        except Exception as e:
            logger.error(f"Failed to initialize SITL: {e}")
            logger.info("Falling back to SIM mode")
            vehicle_client = TelemetrySim()
    else:
        logger.info("Initializing SIM mode...")
        vehicle_client = TelemetrySim()


def telemetry_broadcast_loop():
    """Background thread to broadcast telemetry at TELEMETRY_RATE.

    The loop checks `telemetry_stop_event` to support a responsive shutdown.
    """
    global latest_telemetry

    interval = 1.0 / TELEMETRY_RATE
    logger.info(f"Starting telemetry broadcast at {TELEMETRY_RATE} Hz")

    while not telemetry_stop_event.is_set():
        try:
            # Update simulator state if using simulator
            if isinstance(vehicle_client, TelemetrySim):
                telemetry = vehicle_client.update()

                # Check for command completion
                completion_ack = vehicle_client.check_command_completion()
                if completion_ack:
                    socketio.emit('command_ack', completion_ack)
            else:
                telemetry = vehicle_client.get_telemetry()

            latest_telemetry = telemetry

            # Broadcast telemetry to all connected clients
            socketio.emit('telemetry', telemetry)

        except Exception as e:
            logger.error(f"Error in telemetry broadcast: {e}")

        # Use Event.wait so shutdown can interrupt sleep promptly
        telemetry_stop_event.wait(interval)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    mode = 'SITL' if SIM_MODE == 'SITL' and hasattr(vehicle_client, 'master') else 'SIM'
    return jsonify({
        'status': 'ok',
        'mode': mode
    })


def start_server():
    """Start the server and telemetry broadcast."""
    global running, telemetry_thread, command_controller
    
    # Initialize vehicle client
    initialize_vehicle_client()
    
    # Initialize command controller
    command_controller = CommandController(vehicle_client)
    
    # Register Socket.IO events
    register_socketio_events(socketio, command_controller, lambda: latest_telemetry, AUTO_MODE_SWITCH)
    
    # Start telemetry broadcast thread
    telemetry_stop_event.clear()
    telemetry_thread = threading.Thread(target=telemetry_broadcast_loop, daemon=True)
    telemetry_thread.start()
    
    # Emit initial connection status
    @socketio.on('connect')
    def handle_initial_connect():
        mode = 'SITL' if SIM_MODE == 'SITL' and hasattr(vehicle_client, 'connected') and vehicle_client.connected else 'SIM'
        socketio.emit('conn_status', {
            'status': 'connected',
            'server_time': datetime.now(timezone.utc).isoformat(),
            'mode': mode
        })
    
    # Start Flask-SocketIO server
    logger.info(f"Starting server on port {PORT}")
    try:
        socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
    finally:
        # Ensure background threads and clients are stopped on exit
        telemetry_stop_event.set()
        if telemetry_thread and telemetry_thread.is_alive():
            telemetry_thread.join(timeout=2)
        if vehicle_client and hasattr(vehicle_client, 'stop'):
            try:
                vehicle_client.stop()
            except Exception:
                logger.exception('Error stopping vehicle client')


if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        telemetry_stop_event.set()
        if telemetry_thread and telemetry_thread.is_alive():
            telemetry_thread.join(timeout=2)
        if vehicle_client and hasattr(vehicle_client, 'stop'):
            try:
                vehicle_client.stop()
            except Exception:
                logger.exception('Error stopping vehicle client')
        sys.exit(0)

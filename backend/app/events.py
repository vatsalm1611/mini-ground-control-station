"""Socket.IO event registration for the Mini GCS server.

This module keeps event handlers small: validate -> ack -> execute -> notify.
Command execution is delegated to the vehicle client (simulator or MAVLink
client) and the controller performs validation and safety checks.
"""

from flask_socketio import emit  # compatibility import
from app.controllers import CommandController
import logging

logger = logging.getLogger(__name__)


def register_socketio_events(socketio, command_controller: CommandController, get_telemetry_fn, auto_mode_switch: bool = True):
    """Register handlers on the provided Socket.IO server instance.

    Handlers:
    - `disconnect`: log client disconnects
    - `command`: validate and execute incoming commands

    Parameters are intentionally small and easy to test.
    """

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected')

    @socketio.on('command')
    def handle_command(data):
        # Validate and prepare command (returns rejected ack or exec tuple)
        import uuid as _uuid
        logger.info('Received command: %s', data)
        telemetry = get_telemetry_fn() if callable(get_telemetry_fn) else None

        rejected, exec_tuple = command_controller.prepare_command(data, telemetry)
        if rejected:
            socketio.emit('command_ack', rejected)
            logger.info('Sent command_ack: %s', rejected)
            return

        cmd_id, cmd_type, params = exec_tuple

        # Special-case: if vehicle is in HOLD and client requests GOTO, optionally
        # switch mode to GUIDED automatically before sending the GOTO command.
        if cmd_type == 'goto' and telemetry and telemetry.get('mode') == 'HOLD':
            if not auto_mode_switch:
                rej = {"id": cmd_id, "status": "rejected", "reason": "Vehicle in HOLD — set mode to GUIDED to accept GOTO"}
                socketio.emit('command_ack', rej)
                return

            helper_id = str(_uuid.uuid4())
            socketio.emit('command_ack', {"id": helper_id, "status": "accepted", "reason": None})
            try:
                set_res = command_controller.vehicle_client.send_command('set_mode', {"mode": "GUIDED"}, helper_id)
                if isinstance(set_res, dict):
                    socketio.emit('command_ack', set_res)
            except Exception as e:
                socketio.emit('command_ack', {"id": helper_id, "status": "failed", "reason": str(e)})
                socketio.emit('command_ack', {"id": cmd_id, "status": "rejected", "reason": "Mode change failed — cannot send GOTO"})
                return

        # Acknowledge and then execute. Execution results (executing/completed/failed)
        # are emitted back to clients as `command_ack` messages.
        socketio.emit('command_ack', {"id": cmd_id, "status": "accepted", "reason": None})
        try:
            result = command_controller.vehicle_client.send_command(cmd_type, params, cmd_id)
            if isinstance(result, dict) and result.get('status') in ("executing", "completed", "failed"):
                socketio.emit('command_ack', result)
                logger.info('Sent command_ack: %s', result)
        except Exception as e:
            failed = {"id": cmd_id, "status": "failed", "reason": str(e)}
            socketio.emit('command_ack', failed)
            logger.error('Command execution failed: %s', e)

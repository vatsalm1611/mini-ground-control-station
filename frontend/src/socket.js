/**
 * SocketClient: small wrapper around socket.io-client used by the UI.
 * Responsibilities:
 *  - manage connection lifecycle
 *  - provide `on`, `off`, `emit` helpers
 *  - expose `isConnected()` for UI state
 */
import { io } from 'socket.io-client';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

class SocketClient {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.listeners = {};
  }

  connect() {
    if (this.socket) {
      return this.socket;
    }

    this.socket = io(BACKEND_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    this.socket.on('connect', () => {
      console.log('Socket connected');
      this.connected = true;
    });

    this.socket.on('disconnect', () => {
      console.log('Socket disconnected');
      this.connected = false;
    });

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }

  on(event, callback) {
    if (!this.socket) {
      this.connect();
    }
    this.socket.on(event, callback);
  }

  off(event, callback) {
    if (this.socket) {
      this.socket.off(event, callback);
    }
  }

  emit(event, data) {
    if (!this.socket) {
      this.connect();
    }
    this.socket.emit(event, data);
  }

  isConnected() {
    return this.connected;
  }
}

// Export singleton instance
const socketClient = new SocketClient();
export default socketClient;

/**
 * App: root React component for Mini GCS.
 * Wires socket client to UI components and maintains app-level state
 * (telemetry, waypoints, connection status, pending commands).
 */
import React, { useState, useEffect } from 'react';
import socketClient from './socket';
import MapView from './components/MapView';
import TelemetryPanel from './components/TelemetryPanel';
import Controls from './components/Controls';
import MissionUploader from './components/MissionUploader';
import './App.css';
import { Toaster, toast } from 'react-hot-toast';

function App() {
  const [telemetry, setTelemetry] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [serverMode, setServerMode] = useState('SIM');
  const [commandAcks, setCommandAcks] = useState([]);
  const [waypoints, setWaypoints] = useState([]);
  const [pendingById, setPendingById] = useState(new Map()); // id -> type
  const [pendingTypes, setPendingTypes] = useState(new Set()); // types pending
  const [gotoTarget, setGotoTarget] = useState(null); // {lat, lon}

  useEffect(() => {
    // Connect to socket
    socketClient.connect();

    // Listen for connection status
    socketClient.on('conn_status', (data) => {
      console.log('Connection status:', data);
      setConnectionStatus(data.status);
      setServerMode(data.mode);
    });

    // Listen for telemetry
    socketClient.on('telemetry', (data) => {
      setTelemetry(data);
    });

    // Listen for command acknowledgments
    socketClient.on('command_ack', (data) => {
      console.log('Command ack:', data);
      setCommandAcks((prev) => {
        const newAcks = [...prev, { ...data, timestamp: new Date().toISOString() }];
        if (newAcks.length > 10) return newAcks.slice(-10);
        return newAcks;
      });

      // Toast feedback
      if (data.status === 'accepted') toast.success('Command accepted');
      else if (data.status === 'executing') toast('Command executing...', { icon: '⏳' });
      else if (data.status === 'completed') toast.success('Command completed');
      else if (data.status === 'rejected') toast.error(data.reason || 'Command rejected');
      else if (data.status === 'failed') toast.error(`Failed: ${data.reason || ''}`);

      // Clear pending when terminal status
      if (['completed', 'rejected', 'failed'].includes(data.status)) {
        setPendingById((prev) => {
          const next = new Map(prev);
          const type = next.get(data.id);
          next.delete(data.id);
          if (type) {
            setPendingTypes((prevTypes) => {
              const n = new Set(prevTypes);
              n.delete(type);
              return n;
            });
          }
          return next;
        });
      }
    });

    // Listen for errors
    socketClient.on('error', (data) => {
      console.error('Server error:', data);
      alert(`Error: ${data.message}`);
    });

    // Cleanup on unmount
    return () => {
      socketClient.disconnect();
    };
  }, []);

  const handleSendCommand = (command) => {
    console.log('Sending command:', command);
    setPendingById((prev) => {
      const next = new Map(prev);
      next.set(command.id, command.type);
      return next;
    });
    setPendingTypes((prev) => new Set(prev).add(command.type));
    socketClient.emit('command', command);
  };

  const handleUploadMission = (command) => {
    console.log('Uploading mission:', command);
    handleSendCommand(command);
    if (command.params && command.params.mission) {
      setWaypoints(command.params.mission);
    }
  };

  const canDisarm = !!(telemetry?.armed && (telemetry?.position?.relative_alt ?? 0) <= 0.5 && (telemetry?.velocity?.speed ?? 0) <= 0.5);
  const disarmReason = telemetry?.armed ? (!canDisarm ? 'Cannot disarm while airborne or moving' : '') : 'Already disarmed';

  return (
    <div className="app">
      <header className="app-header">
        <h1>Mini Ground Control Station</h1>
        <div className="header-status">
          <span className={`status-indicator ${connectionStatus}`}>
            {connectionStatus === 'connected' ? '● Connected' : '○ Disconnected'}
          </span>
          <span className="mode-indicator">Mode: {serverMode}</span>
        </div>
      </header>

      <Toaster position="top-center" />

      <div className="app-body">
        <div className="left-panel">
          <MapView
            telemetry={telemetry}
            waypoints={waypoints}
            onSelectCoordinate={(lat, lon) => setGotoTarget({ lat, lon })}
          />
        </div>

        <div className="center-panel">
          <TelemetryPanel telemetry={telemetry} />
        </div>

        <div className="right-panel">
          <Controls
            onSendCommand={handleSendCommand}
            armed={telemetry?.armed || false}
            mode={telemetry?.mode || 'UNKNOWN'}
            telemetry={telemetry}
            canDisarm={canDisarm}
            disarmDisabledReason={disarmReason}
            isPending={(type) => pendingTypes.has(type)}
            externalGotoTarget={gotoTarget}
          />
<MissionUploader onUploadMission={handleUploadMission} />
        </div>
      </div>

      <div className="app-footer">
        <div className="command-acks">
          <h4>Recent Command Acknowledgments</h4>
          {commandAcks.length === 0 ? (
            <p>No commands yet</p>
          ) : (
            <ul>
              {commandAcks.slice().reverse().map((ack, idx) => (
                <li key={idx} className={`ack-${ack.status}`}>
                  <strong>{ack.status.toUpperCase()}</strong> - ID: {ack.id.substring(0, 8)}...
                  {ack.reason && ` (${ack.reason})`}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;

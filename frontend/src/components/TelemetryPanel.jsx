/**
 * TelemetryPanel component
 * Shows the most recent telemetry values: position, attitude, velocity,
 * system mode/armed status and battery. Expects the backend telemetry shape.
 * Props:
 *  - telemetry: telemetry object matching backend schema
 */
import React from 'react';
import PropTypes from 'prop-types';

const TelemetryPanel = ({ telemetry }) => {
  if (!telemetry || !telemetry.position) {
    return (
      <div className="telemetry-panel">
        <h3>Telemetry</h3>
        <p>Waiting for telemetry data...</p>
      </div>
    );
  }

  const { position, attitude, velocity, battery, mode, armed } = telemetry;

  return (
    <div className="telemetry-panel">
      <h3>Telemetry</h3>
      
      <div className="telemetry-section">
        <h4>Position</h4>
        <div className="telemetry-row">
          <span className="label">Lat:</span>
          <span className="value">{position.lat.toFixed(6)}°</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Lon:</span>
          <span className="value">{position.lon.toFixed(6)}°</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Alt (AGL):</span>
          <span className="value">{position.relative_alt.toFixed(1)} m</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Alt (MSL):</span>
          <span className="value">{position.alt.toFixed(1)} m</span>
        </div>
      </div>

      <div className="telemetry-section">
        <h4>Attitude</h4>
        <div className="telemetry-row">
          <span className="label">Roll:</span>
          <span className="value">{attitude.roll.toFixed(1)}°</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Pitch:</span>
          <span className="value">{attitude.pitch.toFixed(1)}°</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Yaw:</span>
          <span className="value">{attitude.yaw.toFixed(1)}°</span>
        </div>
      </div>

      <div className="telemetry-section">
        <h4>Velocity</h4>
        <div className="telemetry-row">
          <span className="label">Speed:</span>
          <span className="value">{velocity.speed.toFixed(1)} m/s</span>
        </div>
        <div className="telemetry-row">
          <span className="label">VZ:</span>
          <span className="value">{velocity.vz.toFixed(1)} m/s</span>
        </div>
      </div>

      <div className="telemetry-section">
        <h4>System</h4>
        <div className="telemetry-row">
          <span className="label">Mode:</span>
          <span className={`value mode-${mode.toLowerCase()}`}>{mode}</span>
        </div>
        <div className="telemetry-row">
          <span className="label">Armed:</span>
          <span className={`value ${armed ? 'armed' : 'disarmed'}`}>
            {armed ? 'YES' : 'NO'}
          </span>
        </div>
        <div className="telemetry-row">
          <span className="label">Battery:</span>
          <span className={`value battery-${battery.level > 50 ? 'good' : battery.level > 20 ? 'medium' : 'low'}`}>
            {battery.level}% ({battery.voltage.toFixed(1)}V)
          </span>
        </div>
      </div>
    </div>
  );
};

TelemetryPanel.propTypes = {
  telemetry: PropTypes.shape({
    position: PropTypes.shape({
      lat: PropTypes.number.isRequired,
      lon: PropTypes.number.isRequired,
      alt: PropTypes.number.isRequired,
      relative_alt: PropTypes.number.isRequired,
    }),
    attitude: PropTypes.shape({
      roll: PropTypes.number.isRequired,
      pitch: PropTypes.number.isRequired,
      yaw: PropTypes.number.isRequired,
    }),
    velocity: PropTypes.shape({
      vx: PropTypes.number.isRequired,
      vy: PropTypes.number.isRequired,
      vz: PropTypes.number.isRequired,
      speed: PropTypes.number.isRequired,
    }),
    battery: PropTypes.shape({
      voltage: PropTypes.number.isRequired,
      current: PropTypes.number,
      level: PropTypes.number.isRequired,
    }),
    mode: PropTypes.string.isRequired,
    armed: PropTypes.bool.isRequired,
  }),
};

export default TelemetryPanel;

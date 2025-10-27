/**
 * MissionUploader component
 * Allows users to upload mission waypoints as JSON. Performs basic validation
 * on waypoint structure and sends an `upload_mission` command via the
 * provided `onUploadMission` callback.
 * Props:
 *  - onUploadMission(command)
 */
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { toast } from 'react-hot-toast';

// Simple UUID generator
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

const MissionUploader = ({ onUploadMission }) => {
  const [missionJson, setMissionJson] = useState('');
  const [error, setError] = useState('');

  const sampleMission = [
    { lat: 26.5, lon: 80.3, alt: 10, command: 16 },
    { lat: 26.51, lon: 80.31, alt: 15, command: 16 },
    { lat: 26.52, lon: 80.32, alt: 20, command: 16 },
  ];

  const handleUpload = () => {
    setError('');

    try {
      const mission = JSON.parse(missionJson);

      // Validate mission structure
      if (!Array.isArray(mission)) {
        throw new Error('Mission must be an array of waypoints');
      }

      if (mission.length === 0) {
        throw new Error('Mission must contain at least one waypoint');
      }

      // Validate each waypoint
      mission.forEach((wp, idx) => {
        if (typeof wp.lat !== 'number' || typeof wp.lon !== 'number' || typeof wp.alt !== 'number') {
          throw new Error(`Waypoint ${idx} must have lat, lon, and alt as numbers`);
        }
        if (wp.lat < -90 || wp.lat > 90) {
          throw new Error(`Waypoint ${idx} latitude out of range (-90 to 90)`);
        }
        if (wp.lon < -180 || wp.lon > 180) {
          throw new Error(`Waypoint ${idx} longitude out of range (-180 to 180)`);
        }
        if (wp.alt <= 0) {
          throw new Error(`Waypoint ${idx} altitude must be positive`);
        }
      });

      // Send upload_mission command
      const command = {
        id: generateUUID(),
        type: 'upload_mission',
        params: { mission },
      };

      onUploadMission(command);
      setError('');
      toast.success('Mission uploaded successfully!');
    } catch (err) {
      const msg = `Error: ${err.message}`;
      setError(msg);
      toast.error(msg);
    }
  };

  const loadSample = () => {
    setMissionJson(JSON.stringify(sampleMission, null, 2));
    setError('');
  };

  return (
    <div className="mission-uploader">
      <h3>Mission Uploader</h3>
      
      <div className="mission-controls">
        <button className="btn btn-sample" onClick={loadSample}>
          Load Sample Mission
        </button>
      </div>

      <textarea
        className="mission-textarea"
        value={missionJson}
        onChange={(e) => setMissionJson(e.target.value)}
        placeholder="Paste mission JSON here..."
        rows="10"
      />

      {error && <div className="error-message">{error}</div>}

      <button className="btn btn-upload" onClick={handleUpload}>
        Upload Mission
      </button>


      <div className="mission-help">
        <h4>Mission Format</h4>
        <pre>{`[
  { "lat": 26.5, "lon": 80.3, "alt": 10, "command": 16 },
  { "lat": 26.51, "lon": 80.31, "alt": 15, "command": 16 }
]`}</pre>
        <p>
          <strong>lat/lon:</strong> Decimal degrees<br />
          <strong>alt:</strong> Altitude in meters (AGL)<br />
          <strong>command:</strong> MAVLink command ID (16 = NAV_WAYPOINT)
        </p>
      </div>
    </div>
  );
};

MissionUploader.propTypes = {
  onUploadMission: PropTypes.func.isRequired,
};

export default MissionUploader;

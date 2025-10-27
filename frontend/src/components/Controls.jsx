/**
 * Controls component (Mission Control)
 * Provides buttons and inputs for: Arm/Disarm, Takeoff, Goto, Return (RTL),
 * and Start Mission. Validates user input and emits commands via the
 * supplied `onSendCommand` callback.
 * Props:
 *  - onSendCommand(command)
 *  - armed, mode, telemetry, isPending(type), externalGotoTarget, canDisarm
 */
import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { toast } from 'react-hot-toast';

const generateUUID = () => (typeof crypto !== 'undefined' && crypto.randomUUID
  ? crypto.randomUUID()
  : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    })
);

const Controls = ({ onSendCommand, armed, mode, telemetry, isPending, externalGotoTarget, canDisarm, disarmDisabledReason }) => {
  const [takeoffAlt, setTakeoffAlt] = useState(10);
  const [gotoLat, setGotoLat] = useState(26.51);
  const [gotoLon, setGotoLon] = useState(80.31);
  const [gotoAlt, setGotoAlt] = useState(15);
  const [gotoSpeed, setGotoSpeed] = useState('');
  const [awaitGuidedGoto, setAwaitGuidedGoto] = useState(null);
  const AUTO_MODE_SWITCH = true;

  useEffect(() => {
    if (externalGotoTarget && typeof externalGotoTarget.lat === 'number' && typeof externalGotoTarget.lon === 'number') {
      setGotoLat(Number(externalGotoTarget.lat.toFixed(6)));
      setGotoLon(Number(externalGotoTarget.lon.toFixed(6)));
    }
  }, [externalGotoTarget]);

  const send = (type, params={}) => onSendCommand({ id: generateUUID(), type, params });
  const pending = (type) => !!(isPending && isPending(type));

  const autoArmIfNeeded = async () => {
    if (!armed) {
      toast('Arming...');
      send('arm');
      // rely on ack lifecycle; user can re-click after ack, or we proceed in SIM anyway
    }
  };

  const handleTakeoff = async () => {
    if (!takeoffAlt || takeoffAlt <= 0) return toast.error('Takeoff altitude must be > 0 m');
    await autoArmIfNeeded();
    if (pending('takeoff')) return toast('Takeoff already pending');
    send('takeoff', { alt: takeoffAlt });
  };

  const handleGoto = async () => {
    const lat = gotoLat, lon = gotoLon, alt = gotoAlt;
    const speed = gotoSpeed ? parseFloat(gotoSpeed) : undefined;
    if (lat < -90 || lat > 90) return toast.error('Latitude must be between -90 and 90');
    if (lon < -180 || lon > 180) return toast.error('Longitude must be between -180 and 180');
    if (!alt || alt <= 0) return toast.error('Goto altitude must be > 0 m');
    if (pending('goto')) return toast('Goto already pending');

    await autoArmIfNeeded();
    const params = { lat, lon, alt, ...(speed ? { speed } : {}) };

    if (mode === 'HOLD' && AUTO_MODE_SWITCH) {
      console.log('[DEBUG] Current mode: HOLD -> switching to GUIDED');
      toast('Switching to GUIDED...');
      send('set_mode', { mode: 'GUIDED' });
      const timer = setTimeout(() => { setAwaitGuidedGoto(null); toast.error('Mode change failed — cannot send GOTO'); }, 2000);
      setAwaitGuidedGoto({ params, timerId: timer });
      return;
    }
    console.log('[DEBUG] Sending GOTO:', { params });
    send('goto', params);
  };

  useEffect(() => {
    if (awaitGuidedGoto && mode === 'GUIDED') {
      clearTimeout(awaitGuidedGoto.timerId);
      send('goto', awaitGuidedGoto.params);
      setAwaitGuidedGoto(null);
    }
  }, [mode]);

  return (
    <div className="controls-panel">
      <h3>Mission Control</h3>

      <div className="control-section">
        <h4>Arming</h4>
        <div className="button-group">
          <button className="btn btn-arm" onClick={() => send('arm')} disabled={armed || pending('arm')}>Arm</button>
          <div className="disarm-wrap">
            <button className="btn btn-disarm" onClick={() => send('disarm')} disabled={!armed || !canDisarm || pending('disarm')}>Disarm</button>
            {!(!armed || canDisarm) && (
              <small className="helper-text">{disarmDisabledReason || 'Cannot disarm while airborne or moving'}</small>
            )}
          </div>
        </div>
      </div>

      <div className="control-section">
        <h4>Takeoff</h4>
        <div className="input-group">
          <label htmlFor="takeoff-alt">Altitude (m):</label>
          <input id="takeoff-alt" type="number" value={takeoffAlt} onChange={e=>setTakeoffAlt(parseFloat(e.target.value))} min="1" step="1" />
          <button className="btn btn-takeoff" onClick={handleTakeoff} disabled={pending('takeoff')}>Takeoff</button>
        </div>
      </div>

      <div className="control-section">
        <h4>Move to Position</h4>
        <div className="input-group">
          <label htmlFor="goto-lat">Latitude:</label>
          <input id="goto-lat" type="number" value={gotoLat} onChange={e=>setGotoLat(parseFloat(e.target.value))} step="0.000001" />
        </div>
        <div className="input-group">
          <label htmlFor="goto-lon">Longitude:</label>
          <input id="goto-lon" type="number" value={gotoLon} onChange={e=>setGotoLon(parseFloat(e.target.value))} step="0.000001" />
        </div>
        <div className="input-group">
          <label htmlFor="goto-alt">Altitude (m):</label>
          <input id="goto-alt" type="number" value={gotoAlt} onChange={e=>setGotoAlt(parseFloat(e.target.value))} min="1" step="1" />
        </div>
        <div className="input-group">
          <button className="btn btn-fill" onClick={() => {
            if (!telemetry || !telemetry.position) return;
            setGotoLat(Number(telemetry.position.lat.toFixed(6)));
            setGotoLon(Number(telemetry.position.lon.toFixed(6)));
            setGotoAlt(Math.max(1, Math.round((telemetry.position.relative_alt || 1))));
          }}>Fill from telemetry</button>
        </div>
        <div className="input-group">
          <label htmlFor="goto-speed">Speed (m/s, optional):</label>
          <input id="goto-speed" type="number" value={gotoSpeed} onChange={e=>setGotoSpeed(e.target.value)} min="0.1" step="0.1" />
          <button className="btn btn-goto" onClick={handleGoto} disabled={pending('goto')}>Goto</button>
        </div>
      </div>

      <div className="control-section">
        <h4>Return to Home</h4>
        <div className="button-group">
          <button className="btn btn-rtl" onClick={()=>send('rtl')} disabled={pending('rtl')}>Return (RTL)</button>
          <button className="btn btn-land" onClick={()=>send('set_mode', { mode: 'LAND' })} disabled={pending('set_mode')}>Land</button>
        </div>
      </div>

      <div className="control-section">
        <h4>Mission</h4>
        <div className="button-group">
          <button className="btn btn-start-mission" onClick={()=>send('start_mission')} disabled={pending('start_mission')}>Start Mission</button>
        </div>
      </div>

    </div>
  );
};

Controls.propTypes = {
  onSendCommand: PropTypes.func.isRequired,
  armed: PropTypes.bool,
  mode: PropTypes.string,
  telemetry: PropTypes.object,
  isPending: PropTypes.func,
  externalGotoTarget: PropTypes.shape({ lat: PropTypes.number, lon: PropTypes.number }),
  canDisarm: PropTypes.bool,
  disarmDisabledReason: PropTypes.string,
};

Controls.defaultProps = {
  armed: false,
  mode: 'UNKNOWN',
  telemetry: null,
  isPending: () => false,
  externalGotoTarget: null,
  canDisarm: true,
  disarmDisabledReason: '',
};

export default Controls;

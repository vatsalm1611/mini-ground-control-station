/**
 * MapView component
 * Renders the drone's current position and trajectory on a Mapbox GL map.
 * Falls back to a simple canvas view when no Mapbox token is provided.
 * Props:
 *  - telemetry: latest telemetry object
 *  - waypoints: array of mission waypoints
 *  - onSelectCoordinate(lat, lon): callback when user selects a point on map
 */
import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

const MapView = ({ telemetry, waypoints, onSelectCoordinate }) => {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const [useMapbox, setUseMapbox] = useState(!!MAPBOX_TOKEN);
  const [trajectory, setTrajectory] = useState([]);

  useEffect(() => {
    if (!telemetry || !telemetry.position) return;

    // Add to trajectory
    const { lat, lon } = telemetry.position;
    setTrajectory((prev) => {
      const newTrajectory = [...prev, { lat, lon }];
      // Keep last 100 points
      if (newTrajectory.length > 100) {
        return newTrajectory.slice(-100);
      }
      return newTrajectory;
    });
  }, [telemetry]);

  useEffect(() => {
    if (!mapContainer.current || !useMapbox || !MAPBOX_TOKEN) {
      return;
    }

    // Try to load Mapbox GL
    const loadMapbox = async () => {
      try {
        const { default: mapboxgl } = await import('mapbox-gl');
        mapboxgl.accessToken = MAPBOX_TOKEN;

        const map = new mapboxgl.Map({
          container: mapContainer.current,
          style: 'mapbox://styles/mapbox/satellite-streets-v12',
          center: [80.3, 26.5],
          zoom: 14,
        });

        map.on('load', () => {
          // Add drone marker source
          map.addSource('drone', {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'Point',
                coordinates: [80.3, 26.5],
              },
            },
          });

          // Add drone marker layer
          map.addLayer({
            id: 'drone-marker',
            type: 'circle',
            source: 'drone',
            paint: {
              'circle-radius': 8,
              'circle-color': '#ff0000',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
            },
          });

          // Add trajectory line source
          map.addSource('trajectory', {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: [],
              },
            },
          });

          // Add trajectory line layer
          map.addLayer({
            id: 'trajectory-line',
            type: 'line',
            source: 'trajectory',
            paint: {
              'line-color': '#00ff00',
              'line-width': 2,
            },
          });

          // Add mission waypoints source
          map.addSource('mission', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: [],
            },
          });

          // Circles for waypoints
          map.addLayer({
            id: 'mission-points',
            type: 'circle',
            source: 'mission',
            paint: {
              'circle-radius': 5,
              'circle-color': '#0077ff',
              'circle-stroke-width': 1,
              'circle-stroke-color': '#ffffff',
            },
          });

          // Numbers for waypoints
          map.addLayer({
            id: 'mission-labels',
            type: 'symbol',
            source: 'mission',
            layout: {
              'text-field': ['to-string', ['get', 'seq']],
              'text-size': 12,
              'text-offset': [0, 1.2],
            },
            paint: { 'text-color': '#ffffff' },
          });

          // Map click handler for Goto
          map.on('click', (e) => {
            if (onSelectCoordinate) onSelectCoordinate(e.lngLat.lat, e.lngLat.lng);
          });

          mapRef.current = map;
        });

        return () => map.remove();
      } catch (error) {
        console.error('Failed to load Mapbox:', error);
        setUseMapbox(false);
      }
    };

    loadMapbox();
  }, [useMapbox]);

  // Update map when telemetry changes
  useEffect(() => {
    if (!mapRef.current || !telemetry || !telemetry.position) return;

    const { lat, lon } = telemetry.position;
    const { yaw } = telemetry.attitude;

    // Ensure sources exist
    if (!mapRef.current.getSource('drone')) {
      mapRef.current.addSource('drone', {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'Point', coordinates: [lon, lat] } },
      });
      if (!mapRef.current.getLayer('drone-marker')) {
        mapRef.current.addLayer({
          id: 'drone-marker', type: 'circle', source: 'drone',
          paint: {
            'circle-radius': 8,
            'circle-color': '#ff0000',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff',
          },
        });
      }
    } else {
      const droneSource = mapRef.current.getSource('drone');
      droneSource.setData({ type: 'Feature', geometry: { type: 'Point', coordinates: [lon, lat] } });
    }

    if (!mapRef.current.getSource('trajectory')) {
      mapRef.current.addSource('trajectory', {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'LineString', coordinates: [] } },
      });
      if (!mapRef.current.getLayer('trajectory-line')) {
        mapRef.current.addLayer({
          id: 'trajectory-line', type: 'line', source: 'trajectory',
          paint: { 'line-color': '#00ff00', 'line-width': 2 },
        });
      }
    } else if (trajectory.length > 0) {
      const trajectorySource = mapRef.current.getSource('trajectory');
      trajectorySource.setData({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: trajectory.map((p) => [p.lon, p.lat]) },
      });
    }

    // Center map on drone
    mapRef.current.easeTo({
      center: [lon, lat],
      duration: 1000,
    });
  }, [telemetry, trajectory]);

  // Update mission waypoints on map
  useEffect(() => {
    if (!mapRef.current) return;
    const missionSource = mapRef.current.getSource('mission');
    if (missionSource) {
      const features = (waypoints || []).map((wp, idx) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [wp.lon, wp.lat] },
        properties: { seq: idx + 1 },
      }));
      missionSource.setData({ type: 'FeatureCollection', features });
    }
  }, [waypoints]);

  // Fallback simple display if Mapbox not available
  if (!useMapbox || !MAPBOX_TOKEN) {
    return (
      <div className="map-view fallback">
        <h3>Map (Fallback Mode)</h3>
        {telemetry && telemetry.position ? (
          <div className="fallback-display">
            <div className="position-display">
              <p>Lat: {telemetry.position.lat.toFixed(6)}°</p>
              <p>Lon: {telemetry.position.lon.toFixed(6)}°</p>
              <p>Heading: {telemetry.attitude.yaw.toFixed(1)}°</p>
            </div>
            <canvas
              onClick={(e) => {
                if (!onSelectCoordinate) return;
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const width = e.currentTarget.width;
                const height = e.currentTarget.height;
                // Inverse of drawing transform used below
                const lon = 80.2 + (x - width/2) / 10000;
                const lat = 26.6 - (y - height/2) / 10000;
                onSelectCoordinate(lat, lon);
              }}
              ref={(canvas) => {
                if (!canvas || !telemetry) return;
                if (typeof canvas.getContext !== 'function') return;
                const ctx = canvas.getContext('2d');
                if (!ctx) return;
                const width = canvas.width;
                const height = canvas.height;

                // Clear
                ctx.clearRect(0, 0, width, height);

                // Draw background
                ctx.fillStyle = '#1a1a1a';
                ctx.fillRect(0, 0, width, height);

                // Draw trajectory
                if (trajectory.length > 1) {
                  ctx.strokeStyle = '#00ff00';
                  ctx.lineWidth = 2;
                  ctx.beginPath();
                  trajectory.forEach((point, i) => {
                    const x = (point.lon - 80.2) * 10000 + width / 2;
                    const y = (26.6 - point.lat) * 10000 + height / 2;
                    if (i === 0) {
                      ctx.moveTo(x, y);
                    } else {
                      ctx.lineTo(x, y);
                    }
                  });
                  ctx.stroke();
                }

                // Draw mission waypoints
                if (Array.isArray(waypoints) && waypoints.length > 0) {
                  ctx.fillStyle = '#0077ff';
                  ctx.strokeStyle = '#ffffff';
                  ctx.lineWidth = 1;
                  waypoints.forEach((wp, idx) => {
                    const wx = (wp.lon - 80.2) * 10000 + width / 2;
                    const wy = (26.6 - wp.lat) * 10000 + height / 2;
                    ctx.beginPath();
                    ctx.arc(wx, wy, 5, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.stroke();
                    ctx.fillStyle = '#ffffff';
                    ctx.font = '12px sans-serif';
                    ctx.fillText(String(idx + 1), wx + 6, wy - 6);
                    ctx.fillStyle = '#0077ff';
                  });
                }

                // Draw drone
                const { lat, lon } = telemetry.position;
                const x = (lon - 80.2) * 10000 + width / 2;
                const y = (26.6 - lat) * 10000 + height / 2;

                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(x, y, 8, 0, Math.PI * 2);
                ctx.fill();

                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2;
                ctx.stroke();

                // Draw heading line
                const yaw = (telemetry.attitude.yaw * Math.PI) / 180;
                const lineLen = 20;
                ctx.strokeStyle = '#ffffff';
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x + Math.sin(yaw) * lineLen, y - Math.cos(yaw) * lineLen);
                ctx.stroke();
              }}
              width="400"
              height="300"
              style={{ border: '1px solid #444', marginTop: '10px' }}
            />
            <p className="fallback-note">
              Mapbox token not configured. Add VITE_MAPBOX_TOKEN to .env.development for full map.
            </p>
          </div>
        ) : (
          <p>Waiting for telemetry...</p>
        )}
      </div>
    );
  }

  return (
    <div className="map-view">
      <div ref={mapContainer} className="map-container" />
    </div>
  );
};

MapView.propTypes = {
  telemetry: PropTypes.object,
  waypoints: PropTypes.arrayOf(
    PropTypes.shape({
      lat: PropTypes.number.isRequired,
      lon: PropTypes.number.isRequired,
    })
  ),
  onSelectCoordinate: PropTypes.func,
};

MapView.defaultProps = {
  waypoints: [],
};

export default MapView;

/**
 * Tests for MapView component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import MapView from '../components/MapView';

describe('MapView Component', () => {
  const mockTelemetry = {
    position: {
      lat: 26.5,
      lon: 80.3,
      alt: 100.0,
      relative_alt: 10.5,
    },
    attitude: {
      roll: 0.0,
      pitch: 0.0,
      yaw: 45.0,
    },
    velocity: {
      vx: 1.0,
      vy: 1.0,
      vz: 0.0,
      speed: 1.4,
    },
    battery: {
      voltage: 12.6,
      current: 5.0,
      level: 85,
    },
    mode: 'GUIDED',
    armed: true,
  };

  it('renders fallback mode when no Mapbox token', () => {
    render(<MapView telemetry={null} waypoints={[]} />);
    
    expect(screen.getByText(/Map \(Fallback Mode\)/)).toBeInTheDocument();
  });

  it('shows waiting message when no telemetry', () => {
    render(<MapView telemetry={null} waypoints={[]} />);
    
    expect(screen.getByText(/Waiting for telemetry/)).toBeInTheDocument();
  });

  it('displays position in fallback mode', () => {
    render(<MapView telemetry={mockTelemetry} waypoints={[]} />);
    
    expect(screen.getByText(/Lat: 26.500000°/)).toBeInTheDocument();
    expect(screen.getByText(/Lon: 80.300000°/)).toBeInTheDocument();
    expect(screen.getByText(/Heading: 45.0°/)).toBeInTheDocument();
  });

  it('renders canvas in fallback mode', () => {
    const { container } = render(<MapView telemetry={mockTelemetry} waypoints={[]} />);
    
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveAttribute('width', '400');
    expect(canvas).toHaveAttribute('height', '300');
  });

  it('updates when telemetry changes', async () => {
    const { rerender } = render(<MapView telemetry={mockTelemetry} waypoints={[]} />);
    
    const updatedTelemetry = {
      ...mockTelemetry,
      position: {
        ...mockTelemetry.position,
        lat: 26.6,
        lon: 80.4,
      },
    };
    
    rerender(<MapView telemetry={updatedTelemetry} waypoints={[]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/Lat: 26.600000°/)).toBeInTheDocument();
      expect(screen.getByText(/Lon: 80.400000°/)).toBeInTheDocument();
    });
  });
});

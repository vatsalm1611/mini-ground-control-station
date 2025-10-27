/**
 * Tests for simplified Controls component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import Controls from '../components/Controls';

describe('Controls (Minimal)', () => {
  it('renders minimal control sections', () => {
    const mockCommand = vi.fn();
    render(<Controls onSendCommand={mockCommand} armed={false} mode="HOLD" />);

    expect(screen.getByText('Mission Control')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Takeoff' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Move to Position' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Return to Home' })).toBeInTheDocument();
  });

  it('emits takeoff with default altitude', async () => {
    const mockCommand = vi.fn();
    render(<Controls onSendCommand={mockCommand} armed={true} mode="GUIDED" />);

    const section = screen.getByRole('heading', { name: 'Takeoff' }).closest('.control-section');
    const btn = within(section).getByRole('button', { name: 'Takeoff' });
    fireEvent.click(btn);

    return waitFor(() => expect(mockCommand).toHaveBeenCalled());
    const cmd = mockCommand.mock.calls[0][0];
    expect(cmd.type).toBe('takeoff');
    expect(cmd.params.alt).toBe(10);
  });

  it('emits goto when GUIDED', async () => {
    const mockCommand = vi.fn();
    render(
      <Controls
        onSendCommand={mockCommand}
        armed={true}
        mode="GUIDED"
        telemetry={{ position: { lat: 26.5, lon: 80.3, relative_alt: 5 } }}
      />
    );

    const section = screen.getByRole('heading', { name: 'Move to Position' }).closest('.control-section');
    const btn = within(section).getByRole('button', { name: 'Goto' });
    fireEvent.click(btn);

    await waitFor(() => expect(mockCommand).toHaveBeenCalled());
    const last = mockCommand.mock.calls[mockCommand.mock.calls.length - 1][0];
    expect(last.type).toBe('goto');
    expect(last.params).toHaveProperty('lat');
    expect(last.params).toHaveProperty('lon');
    expect(last.params).toHaveProperty('alt');
  });
});

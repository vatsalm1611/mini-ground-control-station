/**
 * Controls GOTO auto-mode-switch tests
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import Controls from '../components/Controls';

const renderControls = (props = {}) => {
  const onSendCommand = vi.fn();
  const utils = render(
    <Controls
      onSendCommand={onSendCommand}
      armed={true}
      mode={props.mode ?? 'HOLD'}
      telemetry={props.telemetry ?? { position: { lat: 26.5, lon: 80.3, relative_alt: 0 } }}
      canDisarm={true}
      isPending={() => false}
    />
  );
  return { onSendCommand, ...utils };
};

describe('Controls GOTO auto-mode-switch', () => {
  it('invalid GOTO prevents emit', () => {
    const { onSendCommand } = renderControls({ mode: 'GUIDED' });
const gotoSection = screen.getByRole('heading', { name: 'Move to Position' }).closest('.control-section');
    const altInput = within(gotoSection).getByLabelText('Altitude (m):');
    fireEvent.change(altInput, { target: { value: '0' } });
    const btn = within(gotoSection).getByRole('button', { name: 'Goto' });
    fireEvent.click(btn);
    expect(onSendCommand).not.toHaveBeenCalled();
  });

  it('auto-switch emits set_mode then goto', async () => {
    const { onSendCommand, rerender } = renderControls({ mode: 'HOLD' });
    const gotoSection = screen.getByRole('heading', { name: 'Move to Position' }).closest('.control-section');
    const altInput = within(gotoSection).getByLabelText('Altitude (m):');
    fireEvent.change(altInput, { target: { value: '10' } });
    const btn = within(gotoSection).getByRole('button', { name: 'Goto' });
    fireEvent.click(btn);
    // First call should be set_mode
    await waitFor(() => expect(onSendCommand).toHaveBeenCalled());
    const first = onSendCommand.mock.calls[0][0];
    expect(first.type).toBe('set_mode');
    // Simulate mode change to GUIDED -> should emit goto
    rerender(
      <Controls
        onSendCommand={onSendCommand}
        armed={true}
        mode={'GUIDED'}
        telemetry={{ position: { lat: 26.5, lon: 80.3, relative_alt: 0 } }}
        isPending={() => false}
      />
    );
    // Next call should be goto
    await waitFor(() => expect(onSendCommand.mock.calls.some(c => c[0].type === 'goto')).toBe(true));
    const last = onSendCommand.mock.calls[onSendCommand.mock.calls.length - 1][0];
    expect(last.type).toBe('goto');
    expect(last.params).toHaveProperty('lat');
    expect(last.params).toHaveProperty('lon');
    expect(last.params).toHaveProperty('alt');
  });
});

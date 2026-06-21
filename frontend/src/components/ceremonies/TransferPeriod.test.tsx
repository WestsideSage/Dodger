import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TransferPeriod } from './TransferPeriod';

function transferBeat(payload: Record<string, unknown>) {
  return { key: 'transfer_period', beat_index: 2, total_beats: 9, payload: { expiring: [], buyouts: [], ...payload } } as never;
}

const vetoRow = {
  player_id: 'p1', name: 'Vetoed Vet', ovr: 71, ask_k: 40, decision: 'resign',
  veto: true, dealbreaker: 'Wants a contender', dealbreaker_letter: 'A',
};

describe('TransferPeriod (#69 veto-aware latch)', () => {
  it('shows "Won\'t re-sign" and DISABLES the Re-sign button on a veto', () => {
    render(<TransferPeriod beat={transferBeat({ expiring: [vetoRow] })} onTransfer={() => {}} onComplete={() => {}} />);
    const row = screen.getByTestId('transfer-expiring-p1');
    expect(row).toHaveTextContent("Won't re-sign");
    const resign = within(row).getByRole('button', { name: 'Re-sign' });
    expect(resign).toBeDisabled();
  });

  it('keeps the Re-sign button enabled when there is no veto', () => {
    render(<TransferPeriod beat={transferBeat({ expiring: [{ ...vetoRow, player_id: 'p2', veto: false, dealbreaker: undefined, dealbreaker_letter: undefined }] })} onTransfer={() => {}} onComplete={() => {}} />);
    const row = screen.getByTestId('transfer-expiring-p2');
    expect(within(row).getByRole('button', { name: 'Re-sign' })).not.toBeDisabled();
  });
});

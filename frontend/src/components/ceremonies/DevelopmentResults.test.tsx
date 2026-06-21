import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DevelopmentResults } from './DevelopmentResults';

// The `development` beat reads beat.payload.players + beat.payload.training_credit
// (verified against DevelopmentResults.tsx + the OffseasonBeat 'development' variant).
function devBeat(overrides: Record<string, unknown> = {}) {
  return {
    key: 'development', beat_index: 4, total_beats: 9, title: 'Development',
    payload: {
      players: [],
      training_credit: { weeks: 6, week_cap: 4, credited_weeks: 4, per_week_ovr: 0.2, credit_ovr: 0.8 },
      ...overrides,
    },
  } as never;
}

describe('DevelopmentResults', () => {
  it('#72: shows the training-credit receipt with cap disclosure (the .toFixed(1) exception)', () => {
    render(<DevelopmentResults beat={devBeat()} onComplete={() => {}} />);
    const receipt = screen.getByTestId('training-credit-receipt');
    expect(receipt).toHaveTextContent('6 weeks run');
    expect(receipt).toHaveTextContent('(4 credited — cap 4)');
    expect(receipt).toHaveTextContent('+0.8 OVR'); // deliberate one-decimal receipt
  });

  it('#72: hides the receipt entirely when weeks === 0', () => {
    render(<DevelopmentResults beat={devBeat({ training_credit: { weeks: 0, week_cap: 4, credited_weeks: 0, per_week_ovr: 0.2, credit_ovr: 0 } })} onComplete={() => {}} />);
    expect(screen.queryByTestId('training-credit-receipt')).not.toBeInTheDocument();
  });

  it('#71: player-facing OVR deltas render as integers (zero-floats)', () => {
    render(<DevelopmentResults beat={devBeat({
      players: [{ name: 'Grower', delta: 2, ovr_before: 60, ovr_after: 62, attr_deltas: {}, notes: [] }],
    })} onComplete={() => {}} />);
    const delta = screen.getByText('+2');
    expect(delta.textContent).not.toMatch(/\./);
  });
});

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Player } from '../types';
import { PlayerDetailModal } from './PlayerDetailModal';

const P = (over: Record<string, unknown> = {}) => ({
  id: 'p1', name: 'Mara Vex', age: 22, overall: 78, role: 'Sharpshooter',
  potential_tier: 'High', scouting_confidence: 3, potential_ceiling: 92, headroom: 14,
  projected_growth: 'growing', ovr_season_trend: null,
  bio_strongest_attr: 'Accuracy', bio_secondary_attr: 'Power',
  ratings: { accuracy: 80, power: 76, dodge: 70, catch: 68, stamina: 72, tactical_iq: 74 },
  ...over,
}) as unknown as Player;

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('PlayerDetailModal player-card truth (#54, #56)', () => {
  it('#54: release is blocked (not hidden) at the 6-floor with a visible reason', () => {
    render(
      <PlayerDetailModal
        player={P()} onClose={vi.fn()} onRelease={vi.fn().mockResolvedValue(undefined)}
        releaseBlockedReason="Roster is at the 6-player floor — sign someone before releasing." hasOpenPromise={false}
      />,
    );
    const btn = screen.getByTestId('release-player-btn');
    expect(btn).toBeDisabled();                                  // blocked, not hidden
    expect(btn).toHaveAttribute('title', expect.stringContaining('6-player floor'));
  });

  it('#54: the confirm strip discloses free-agency + the broken-promise warning', async () => {
    render(
      <PlayerDetailModal
        player={P()} onClose={vi.fn()} onRelease={vi.fn().mockResolvedValue(undefined)}
        releaseBlockedReason={null} hasOpenPromise
      />,
    );
    await userEvent.click(screen.getByTestId('release-player-btn'));
    const strip = screen.getByTestId('release-confirm-strip');     // anti-strip hook
    expect(within(strip).getByText(/free-agent pool/)).toBeInTheDocument();
    expect(within(strip).getByText(/OPEN promise/)).toBeInTheDocument();
  });

  it('#56: the High-Upside ProofChip shows ONLY when growing + headroom>=12 + age<=23', () => {
    const { rerender } = render(<PlayerDetailModal player={P()} onClose={vi.fn()} />);
    expect(screen.getByText('High Upside')).toBeInTheDocument();
    // break each precondition -> chip gone
    rerender(<PlayerDetailModal player={P({ age: 28 })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
    rerender(<PlayerDetailModal player={P({ headroom: 5 })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
    rerender(<PlayerDetailModal player={P({ projected_growth: 'plateauing' })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
  });

  it('#56: bio narrative reads from real numbers (headroom drives the develop-target line)', () => {
    render(<PlayerDetailModal player={P({ potential_tier: 'High', headroom: 14 })} onClose={vi.fn()} />);
    expect(screen.getByText(/14 OVR of headroom ahead/)).toBeInTheDocument();
  });
});

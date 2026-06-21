// frontend/src/components/dynasty/ProspectCard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { ProspectCard } from './ProspectCard';
import { dynastyApi } from '../../api/client';
import type { DynastyOfficeResponse } from '../../types';

vi.mock('../../api/client', () => ({
  dynastyApi: {
    scoutProspect: vi.fn(),
    contactProspect: vi.fn(),
    visitProspect: vi.fn(),
    focusProspect: vi.fn(),
    makePromise: vi.fn(),
  },
}));

type Prospect = DynastyOfficeResponse['recruiting']['prospects'][number];
type Budget = DynastyOfficeResponse['recruiting']['budget'];

// Shape verified against types.ts: Budget = { scout/contact/visit: [number, number] }.
const budget: Budget = { scout: [0, 3], contact: [0, 2], visit: [0, 1] };

export function baseProspect(overrides: Partial<Prospect> = {}): Prospect {
  return {
    player_id: 'p1',
    name: 'Dax Holloway',
    hometown: 'Granite City',
    public_archetype: 'Sharpshooter',
    public_ovr_band: [62, 71],
    fit_score: 84,
    interest: 40,
    scouted: false,
    pipeline_tier: 3,
    promise_options: [],
    active_promise: null,
    recruiting_status: 'UNSCOUTED',
    interest_evidence: [],
    motivations: [],
    fully_visible: true,
    ...overrides,
  } as Prospect;
}

describe('ProspectCard anti-strip + locked variant (#30, #63)', () => {
  it('beyond-network prospect renders the LOCKED variant with its provenance hook', () => {
    render(
      <ProspectCard
        prospect={baseProspect({ fully_visible: false, reach_band: 'NATIONAL', name: 'Kit Marsh', hometown: 'Far Harbor' })}
        budget={budget}
        onAction={() => {}}
        priority={5}
      />,
    );
    const locked = screen.getByTestId('prospect-card-locked');
    expect(locked).toBeInTheDocument();
    expect(locked).toHaveTextContent('Kit Marsh');
    expect(locked).toHaveTextContent('Far Harbor');
    // No scoutable data leaks: no fit meter / FIT score on a locked card.
    expect(screen.queryByTestId('prospect-card')).not.toBeInTheDocument();
    expect(screen.queryByText('FIT')).not.toBeInTheDocument();
  });

  it('a visible prospect renders the full card hook', () => {
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.getByTestId('prospect-card')).toBeInTheDocument();
  });
});

describe('ProspectCard fog + interaction behaviors', () => {
  it('#24: unscouted prospect hides the dealbreaker behind "scout to reveal"', () => {
    render(
      <ProspectCard
        prospect={baseProspect({ motivations: [{ motivation: 'x', label: 'Playing time', letter: 'A', receipt: 'r' }] })}
        budget={budget}
        onAction={() => {}}
        priority={1}
      />,
    );
    expect(screen.getByText(/scout to reveal/i)).toBeInTheDocument();
    // Negative: the veto copy must NOT appear, and no dealbreaker label leaks through.
    expect(screen.queryByText(/WON'T VERBAL/)).not.toBeInTheDocument();
  });
  it('#24: a base prospect with empty motivations array renders no motivations block at all', () => {
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.queryByTestId('prospect-motivations')).not.toBeInTheDocument();
    expect(screen.queryByText(/WON'T VERBAL/)).not.toBeInTheDocument();
  });
  it('#24: a veto dealbreaker shows WON\'T VERBAL', () => {
    render(
      <ProspectCard
        prospect={baseProspect({
          motivations: [{ motivation: 'x', label: 'P', letter: 'A', receipt: 'r' }],
          dealbreaker: { motivation: 'd', label: 'Wants a contender', letter: 'F', veto: true, receipt: 'r' },
        })}
        budget={budget}
        onAction={() => {}}
        priority={1}
      />,
    );
    expect(screen.getByText(/WON'T VERBAL/)).toBeInTheDocument();
  });
  it('#23 + #21: OVR shows the scouted band via KnownValue (estimated when unscouted)', () => {
    render(
      <ProspectCard
        prospect={baseProspect({ public_ovr_band: [62, 71], scouted: false })}
        budget={budget}
        onAction={() => {}}
        priority={1}
      />,
    );
    expect(screen.getByText('62–71')).toBeInTheDocument();
  });
  it('#65: a refused action says "action not spent" and still refetches the board', async () => {
    vi.mocked(dynastyApi.scoutProspect).mockRejectedValue(new Error('No scout slots'));
    const onAction = vi.fn();
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={onAction} priority={1} />);
    await userEvent.click(screen.getByRole('button', { name: 'Scout' }));
    expect(await screen.findByText(/action not spent/i)).toBeInTheDocument();
    expect(onAction).toHaveBeenCalled();
  });
});

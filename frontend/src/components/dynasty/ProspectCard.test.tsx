// frontend/src/components/dynasty/ProspectCard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ProspectCard } from './ProspectCard';
import type { DynastyOfficeResponse } from '../../types';

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

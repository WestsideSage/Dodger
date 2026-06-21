// frontend/src/components/dynasty/history/AlumniLineage.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AlumniLineage } from './AlumniLineage';
import { POTENTIAL_TIERS } from '../../../domain/tiers';

const alum = (potential_tier: string) => ({
  id: `a-${potential_tier}`, name: `Player ${potential_tier}`, seasons_played: 4,
  career_elims: 120, championships: 1, ovr_final: 78, potential_tier,
});

describe('AlumniLineage tier vocabulary (#26)', () => {
  it('gives every canonical potential tier a DISTINCT tone class (no silent slate-bucket)', () => {
    const { container } = render(<AlumniLineage alumni={POTENTIAL_TIERS.map(alum)} />);
    const badges = Array.from(container.querySelectorAll('[data-tier]'));
    const classByTier = new Map(badges.map((b) => [b.getAttribute('data-tier'), b.className]));
    // Mid/Low/Raw must not collapse into the same class as each other.
    const distinct = new Set(['Mid', 'Low', 'Raw'].map((t) => classByTier.get(t)));
    expect(distinct.size).toBe(3);
  });
  it('renders an honest empty state when there are no alumni', () => {
    render(<AlumniLineage alumni={[]} />);
    expect(screen.getByText('No Alumni Yet')).toBeInTheDocument();
  });
});

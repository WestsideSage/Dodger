import { describe, it, expect } from 'vitest';
import { POTENTIAL_TIERS, potentialRank } from './tiers';

describe('potential tiers', () => {
  it('has a stable, distinct rank for every rendered tier', () => {
    expect(POTENTIAL_TIERS).toEqual(['Elite', 'High', 'Mid', 'Low', 'Raw']);
    const ranks = POTENTIAL_TIERS.map(potentialRank);
    expect(new Set(ranks).size).toBe(POTENTIAL_TIERS.length); // no silent bucket collisions
    expect(potentialRank('Elite')).toBeLessThan(potentialRank('Raw'));
  });
  it('unknown tiers sort last, deterministically', () => {
    expect(potentialRank('Mystery' as never)).toBeGreaterThan(potentialRank('Raw'));
  });
});

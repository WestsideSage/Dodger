import { describe, it, expect } from 'vitest';
import { parseSeasonNumber, formatSeasonLabel, compareSeasonAsc, compareSeasonDesc } from './seasonLabel';

describe('seasonLabel (#96 — centralized parse + numeric sort)', () => {
  it('parses season_N to its number', () => {
    expect(parseSeasonNumber('season_2')).toBe(2);
    expect(parseSeasonNumber('season_10')).toBe(10);
    expect(parseSeasonNumber('SEASON_07')).toBe(7);
  });
  it('returns null for unparseable labels (so callers can sort them last, not crash)', () => {
    expect(parseSeasonNumber('worlds-era')).toBeNull();
    expect(parseSeasonNumber(undefined)).toBeNull();
  });
  it('formats season_N to "Season N", passes other labels through humanized', () => {
    expect(formatSeasonLabel('season_3')).toBe('Season 3');
    expect(formatSeasonLabel(null)).toBe('Unknown season');
  });
  it('sorts NUMERICALLY, not lexically (season_10 after season_2)', () => {
    const ids = ['season_10', 'season_2', 'season_1'];
    expect([...ids].sort(compareSeasonAsc)).toEqual(['season_1', 'season_2', 'season_10']);
    expect([...ids].sort(compareSeasonDesc)).toEqual(['season_10', 'season_2', 'season_1']);
  });
  it('unparseable labels sort after all numbered seasons (deterministic)', () => {
    const ids = ['season_2', 'arc', 'season_1'];
    expect([...ids].sort(compareSeasonAsc)).toEqual(['season_1', 'season_2', 'arc']);
  });
});

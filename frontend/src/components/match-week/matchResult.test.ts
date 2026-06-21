import { describe, it, expect } from 'vitest';
import { formatScoreline, survivorDetail } from './matchResult';

describe('matchResult — the V20 single-payload scoreline contract (#1, #2)', () => {
  it('official match: headline number is GAME POINTS, never the survivor tally', () => {
    // The canonical falsifying case: a 0-0 official draw whose box score carries
    // a 0-3 survivor count. The result must read 0-0 (game points), never 0-3.
    const card = {
      scoring_model: 'official_foam',
      home_game_points: 0,
      away_game_points: 0,
      home_survivors: 0,
      away_survivors: 3,
    };
    const s = formatScoreline(card);
    expect(s.isOfficial).toBe(true);
    expect(s.home.value).toBe(0);
    expect(s.away.value).toBe(0); // game points, NOT 3 survivors
    expect(s.away.survivors).toBe(3); // raw survivors retained for detail only
    expect(s.centerLabel).toMatch(/^Final · /); // ruleset short name appended
    expect(survivorDetail(s.away.survivors, s.isOfficial)).toBe('game points');
  });

  it('official match with real game points reads those points', () => {
    const s = formatScoreline({
      scoring_model: 'official_foam',
      home_game_points: 9,
      away_game_points: 2,
      home_survivors: 1,
      away_survivors: 0,
    });
    expect(s.home.value).toBe(9);
    expect(s.away.value).toBe(2);
  });

  it('legacy match: headline number IS the survivor count, labeled in survivors', () => {
    const s = formatScoreline({
      scoring_model: 'legacy',
      home_survivors: 4,
      away_survivors: 1,
    });
    expect(s.isOfficial).toBe(false);
    expect(s.home.value).toBe(4);
    expect(s.away.value).toBe(1);
    expect(s.centerLabel).toBe('Final');
    expect(survivorDetail(s.home.survivors, s.isOfficial)).toBe('4 survivors');
  });

  it('missing scoring_model is treated as legacy (survivors)', () => {
    const s = formatScoreline({ home_survivors: 2, away_survivors: 5 });
    expect(s.isOfficial).toBe(false);
    expect(s.away.value).toBe(5);
  });

  it('official match missing game points falls back to 0, NOT to survivors', () => {
    const s = formatScoreline({
      scoring_model: 'official_foam',
      home_survivors: 6,
      away_survivors: 6,
    });
    expect(s.home.value).toBe(0); // ?? 0 — never leaks the survivor count
    expect(s.away.value).toBe(0);
  });
});

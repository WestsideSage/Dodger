import { describe, it, expect } from 'vitest';
import { rulesetDisplayName } from './rulesetNames';

describe('rulesetDisplayName (audit #27 never leak impl keys)', () => {
  it('maps known career keys to human names', () => {
    expect(rulesetDisplayName('official_foam')).toContain('Foam');
    expect(rulesetDisplayName('official_foam', 'short')).toBe('Foam Division');
  });

  it('never returns a raw UPPER_SNAKE impl key', () => {
    for (const k of ['OFFICIAL_FOAM', 'official_foam', 'foam-open', 'cloth-open-mixed', 'no-sting-open']) {
      const out = rulesetDisplayName(k);
      expect(out).not.toMatch(/[A-Z_]{4,}/); // no leaked constant-style token
    }
  });

  it('null/empty falls back to a legacy name, not a blank or key', () => {
    expect(rulesetDisplayName(null)).toBe('Legacy survivor scoring');
    expect(rulesetDisplayName('')).toBe('Legacy survivor scoring');
  });
});

// frontend/src/components/dynasty/atRisk.test.ts
import { describe, it, expect } from 'vitest';
import { isAtRisk, lockedSinkKey } from './atRisk';

describe('At-Risk + locked-sink predicates (#63)', () => {
  it('counts a visible low-fit prospect as at-risk', () => {
    expect(isAtRisk({ fully_visible: true, fit_score: 50 })).toBe(true);
  });
  it('excludes a beyond-network (locked) prospect from at-risk even if fit is low/absent', () => {
    expect(isAtRisk({ fully_visible: false, fit_score: 10 })).toBe(false);
    expect(isAtRisk({ fully_visible: false })).toBe(false);
  });
  it('a strong-fit visible prospect is not at-risk', () => {
    expect(isAtRisk({ fully_visible: true, fit_score: 84 })).toBe(false);
  });
  it('locked prospects sort AFTER visible ones', () => {
    expect(lockedSinkKey({ fully_visible: false })).toBeGreaterThan(lockedSinkKey({ fully_visible: true }));
  });
});

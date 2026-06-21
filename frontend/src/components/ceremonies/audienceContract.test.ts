import { describe, it, expectTypeOf } from 'vitest';
import type { AftermathParagraph } from '../../types';

// #29 is owned by the Phase-2 aftermath surface (MatchWeek.tsx groups body
// paragraphs by AftermathParagraph.audience). No ceremonies/* file reads it.
// This guard ensures a Phase-6 type edit can't silently widen/narrow the union
// the P2 consumer depends on.
describe('AftermathParagraph.audience contract (#29 — P2-owned, P6-guarded)', () => {
  it('the audience union is exactly you | them | result', () => {
    expectTypeOf<AftermathParagraph['audience']>().toEqualTypeOf<'you' | 'them' | 'result'>();
  });
});

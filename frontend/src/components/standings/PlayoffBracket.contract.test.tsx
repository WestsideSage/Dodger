// frontend/src/components/standings/PlayoffBracket.contract.test.tsx
import { describe, it, expectTypeOf } from 'vitest';
import { PlayoffBracket } from './PlayoffBracket';
import type { PlayoffBracketResponse } from '../../types';
import type { ComponentProps } from 'react';

describe('PlayoffBracket public contract (frozen for P6/ChampionReveal)', () => {
  it('accepts exactly { data: PlayoffBracketResponse }', () => {
    expectTypeOf<ComponentProps<typeof PlayoffBracket>>().toEqualTypeOf<{ data: PlayoffBracketResponse }>();
  });
});

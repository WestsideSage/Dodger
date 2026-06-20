// frontend/src/components/shell/appContracts.test.ts
import type { ComponentProps } from 'react';
import { describe, it, expect, expectTypeOf } from 'vitest';
import { NAV_RAIL_ATTR } from './appContracts';
import type { MatchWeekMountProps, CommandReplayState } from './appContracts';
// MatchWeek is a NAMED export (MatchWeek.tsx:146 `export function MatchWeek`).
// Import the live component so the published contract is tied to its REAL prop
// type — not a hardcoded union that could silently diverge if MatchWeek changes.
import { MatchWeek } from '../MatchWeek';
import type { MatchReplayResponse } from '../../types';

type LiveMatchWeekProps = ComponentProps<typeof MatchWeek>;

describe('app shell published contract', () => {
  it('names the nav-rail DOM attribute P2 keys its reveal-skip on', () => {
    expect(NAV_RAIL_ATTR).toBe('data-nav-rail');
  });
  it('MatchWeekMountProps tracks the LIVE MatchWeek prop surface (drift-proof, compile-time)', () => {
    // Tie every published field to MatchWeek's REAL prop type. If MatchWeek.tsx's
    // `mode` (or any other prop) changes, this fails the build — the hardcoded
    // union is gone, so the contract cannot silently drift.
    expectTypeOf<MatchWeekMountProps['mode']>().toEqualTypeOf<LiveMatchWeekProps['mode']>();
    expectTypeOf<MatchWeekMountProps['onOpenReplay']>().toEqualTypeOf<LiveMatchWeekProps['onOpenReplay']>();
    expectTypeOf<MatchWeekMountProps['onSimComplete']>().toEqualTypeOf<LiveMatchWeekProps['onSimComplete']>();
    expectTypeOf<MatchWeekMountProps['onAdvanceWeek']>().toEqualTypeOf<LiveMatchWeekProps['onAdvanceWeek']>();
    expectTypeOf<MatchWeekMountProps['onPlanWeek']>().toEqualTypeOf<LiveMatchWeekProps['onPlanWeek']>();
    expectTypeOf<MatchWeekMountProps['onOffseasonBeatChange']>()
      .toEqualTypeOf<LiveMatchWeekProps['onOffseasonBeatChange']>();
    expectTypeOf<MatchWeekMountProps['persistedResult']>().toEqualTypeOf<LiveMatchWeekProps['persistedResult']>();
  });
  it('the whole MatchWeekMountProps is a valid prop bag for the live MatchWeek (assignable)', () => {
    // Anything declared mountable by the contract must actually mount MatchWeek.
    expectTypeOf<MatchWeekMountProps>().toMatchTypeOf<LiveMatchWeekProps>();
  });
  it('still anchors `mode` to the published string literals (canary on the live type)', () => {
    // A redundant literal anchor so a reviewer can read the expected shape AND so a
    // change that widens MatchWeek's `mode` (e.g. to `string`) is caught here too.
    expectTypeOf<LiveMatchWeekProps['mode']>().toEqualTypeOf<'pre-sim' | 'post-sim' | 'offseason'>();
  });
  it('CommandReplayState is the replay payload or null', () => {
    expectTypeOf<CommandReplayState>().toEqualTypeOf<MatchReplayResponse | null>();
  });
});

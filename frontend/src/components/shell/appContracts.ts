// frontend/src/components/shell/appContracts.ts
// Published Phase-1 compile-time contract. P2 imports these to mount MatchWeek
// and to assert the replay state shape without re-reading App.tsx. Keep in lockstep
// with MatchWeek's declared props (MatchWeek.tsx:146-165) and App's commandReplay
// state (App.tsx:48). appContracts.test.ts fails the build if either drifts.
import type { CommandCenterSimResponse, MatchReplayResponse } from '../../types';

/** The mode union MatchWeek switches on (mirrors MatchWeek.tsx MatchWeekMode). */
export type MatchWeekMode = 'pre-sim' | 'post-sim' | 'offseason';

/** Exact props App passes to <MatchWeek/>. P2's PreSimDashboard/aftermath/replay
 *  rebuild must keep MatchWeek mountable with precisely this surface. */
export interface MatchWeekMountProps {
  mode: MatchWeekMode;
  onOpenReplay?: (matchId: string) => void;
  persistedResult?: CommandCenterSimResponse | null;
  onSimComplete?: (result: CommandCenterSimResponse) => void;
  onAdvanceWeek?: () => void;
  onOffseasonBeatChange?: (title: string | null) => void;
  onPlanWeek?: (week: number) => void;
}

/** App's command-center replay overlay state. */
export type CommandReplayState = MatchReplayResponse | null;

/** DOM attribute marking the primary nav rail. P2 rewrites MatchWeek.tsx:334
 *  `closest('.dm-left-nav')` → `closest('[data-nav-rail]')` against THIS name. */
export const NAV_RAIL_ATTR = 'data-nav-rail' as const;

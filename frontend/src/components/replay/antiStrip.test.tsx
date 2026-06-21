import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('../../api/client', () => ({
  commandApi: { highlights: vi.fn().mockResolvedValue({ beats: [] }) },
}));

// jsdom does not implement scrollIntoView (EventLog auto-scrolls the active row).
if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => {};
}

import MatchReplay from '../MatchReplay';
import type { MatchReplayResponse } from '../../types';

// Minimal but real-shaped: one official event with score_state + a playoff frame.
const PAYLOAD = (): MatchReplayResponse =>
  ({
    match_id: 'm1',
    week: 3,
    scoring_model: 'official_foam',
    home_club_id: 'aurora',
    away_club_id: 'granite',
    home_club_name: 'Aurora',
    away_club_name: 'Granite',
    home_game_points: 1,
    away_game_points: 0,
    home_survivors: 2,
    away_survivors: 0,
    key_play_indices: [0],
    report: { turning_point: 'A swing.', turning_point_index: 0, evidence_lanes: [], top_performers: [] },
    game_segments: [],
    moment_events: [],
    // PlayoffFrame shape: { proof_source, title, label } — types.ts:768.
    playoff_frame: { proof_source: 'record:playoff-2031-semi', title: 'Semifinal', label: 'Seed tiebreaker semifinal.' },
    official_state: null,
    proof_events: [
      {
        sequence_index: 0,
        tick: 1,
        game_number: 1,
        thrower_id: 'p1',
        thrower_name: 'A One',
        target_id: 'p2',
        target_name: 'B Two',
        offense_club_id: 'aurora',
        defense_club_id: 'granite',
        resolution: 'eliminated',
        is_key_play: true,
        proof_tags: [],
        summary: 'Hit.',
        detail: '',
        odds: {},
        rolls: {},
        fatigue: {} as never,
        decision_context: {} as never,
        tactic_context: {} as never,
        liability_context: {} as never,
        score_state: {
          home_living: 6,
          away_living: 5,
          home_eliminated_player_ids: [],
          away_eliminated_player_ids: ['p2'],
        },
      },
    ],
  }) as never;

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('replay data-* provenance (anti-strip preconditions)', () => {
  it('keeps the broadcast proof-source hook + current-event card (#30, #37)', async () => {
    render(<MatchReplay data={PAYLOAD()} onContinue={() => {}} />);
    const frame = await screen.findByTestId('playoff-frame');
    expect(frame).toHaveAttribute('data-broadcast-proof-source', 'record:playoff-2031-semi');
    expect(screen.getByTestId('current-event-card')).toBeInTheDocument();
  });
});

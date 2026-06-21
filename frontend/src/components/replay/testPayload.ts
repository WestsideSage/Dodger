import type { MatchReplayResponse, ReplayProofEvent } from '../../types';

// jsdom does not implement scrollIntoView (EventLog auto-scrolls the active row).
if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => {};
}

function proof(over: Partial<ReplayProofEvent>): ReplayProofEvent {
  return {
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
    is_key_play: false,
    proof_tags: [],
    summary: 'A throw.',
    detail: '',
    odds: {},
    rolls: {},
    fatigue: {} as never,
    decision_context: {} as never,
    tactic_context: {} as never,
    liability_context: {} as never,
    score_state: {
      home_living: 6,
      away_living: 6,
      home_eliminated_player_ids: [],
      away_eliminated_player_ids: [],
    },
    ...over,
  } as ReplayProofEvent;
}

/**
 * Multi-event, multi-game official replay payload. The default carries a
 * game-1 hit (p2 out), a game-2 boundary (fresh court), and a turning point
 * index pointing at event 1.
 */
export function makeReplay(over: Partial<MatchReplayResponse> = {}): MatchReplayResponse {
  return {
    match_id: 'm1',
    season_id: '2031',
    week: 3,
    home_club_id: 'aurora',
    home_club_name: 'Aurora',
    away_club_id: 'granite',
    away_club_name: 'Granite',
    winner_club_id: 'aurora',
    winner_name: 'Aurora',
    scoring_model: 'official_foam',
    home_game_points: 1,
    away_game_points: 0,
    home_survivors: 2,
    away_survivors: 0,
    key_play_indices: [1],
    moment_events: [],
    proof_events: [
      proof({
        sequence_index: 0,
        tick: 1,
        game_number: 1,
        resolution: 'eliminated',
        summary: 'Game 1 hit.',
        score_state: {
          home_living: 6,
          away_living: 5,
          home_eliminated_player_ids: [],
          away_eliminated_player_ids: ['p2'],
        },
      }),
      proof({
        sequence_index: 1,
        tick: 4,
        game_number: 1,
        is_key_play: true,
        resolution: 'caught',
        thrower_id: 'p3',
        thrower_name: 'C Three',
        target_id: 'p4',
        target_name: 'D Four',
        offense_club_id: 'granite',
        defense_club_id: 'aurora',
        summary: 'A big catch.',
        score_state: {
          home_living: 5,
          away_living: 5,
          home_eliminated_player_ids: ['p4'],
          away_eliminated_player_ids: ['p2'],
        },
      }),
      proof({
        sequence_index: 2,
        tick: 1,
        game_number: 2,
        resolution: 'eliminated',
        summary: 'Game 2 opens.',
        score_state: {
          home_living: 6,
          away_living: 6,
          home_eliminated_player_ids: [],
          away_eliminated_player_ids: [],
        },
      }),
    ],
    game_segments: [
      {
        game_number: 1,
        winner_club_id: 'aurora',
        result_type: 'elimination',
        home_points: 1,
        away_points: 0,
        home_running_points: 1,
        away_running_points: 0,
        home_final_actives: 5,
        away_final_actives: 0,
        first_proof_index: 0,
        last_proof_index: 1,
      },
      {
        game_number: 2,
        winner_club_id: null,
        result_type: 'no_point',
        home_points: 0,
        away_points: 0,
        home_running_points: 1,
        away_running_points: 0,
        home_final_actives: 6,
        away_final_actives: 6,
        first_proof_index: 2,
        last_proof_index: 2,
      },
    ],
    report: {
      winner_name: 'Aurora',
      match_mvp_player_id: null,
      match_mvp_name: null,
      top_performers: [],
      turning_point: 'The big catch swung it.',
      turning_point_index: 1,
      evidence_lanes: [],
    },
    official_state: null,
    ...over,
  } as MatchReplayResponse;
}

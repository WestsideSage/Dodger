// Canonical presentation of a finished match's scoreline.
//
// A match record carries two parallel scores: the official USAD game-points
// (when run under an official ruleset) and the legacy survivor count. Every
// surface that shows "the score" must pick the same one and label it the same
// way. This module is the single place that decision lives, so the score hero
// and the aftermath match card can never drift apart.

export interface ScorelineFields {
  scoring_model?: string;
  home_game_points?: number;
  away_game_points?: number;
  home_survivors: number;
  away_survivors: number;
}

export interface ScorelineSide {
  // The headline number to show (game points when official, else survivors).
  value: number;
  // Always the raw survivor count, for the supporting detail line.
  survivors: number;
}

export interface MatchScoreline {
  isOfficial: boolean;
  // Label for the center "Final" slot, e.g. "Final (USAD V11)" or "Final".
  centerLabel: string;
  home: ScorelineSide;
  away: ScorelineSide;
}

export function formatScoreline(card: ScorelineFields): MatchScoreline {
  const isOfficial = Boolean(card.scoring_model && card.scoring_model !== 'legacy');
  return {
    isOfficial,
    centerLabel: isOfficial ? `Final (USAD ${card.scoring_model?.toUpperCase()})` : 'Final',
    home: {
      value: isOfficial ? card.home_game_points ?? 0 : card.home_survivors,
      survivors: card.home_survivors,
    },
    away: {
      value: isOfficial ? card.away_game_points ?? 0 : card.away_survivors,
      survivors: card.away_survivors,
    },
  };
}

// Supporting detail under each team's number.
//
// For official matches the headline number is game points (set wins). The
// legacy survivor count is not the result and, on a multi-game match, can
// contradict it — a 0-0 foam draw can carry a box-score survivor tally like
// 0-3 that reads as a win the player never got. So we label the unit ("game
// points") rather than print an unreliable survivor count. Legacy matches keep
// the literal survivor count.
export function survivorDetail(survivors: number, isOfficial: boolean): string {
  return isOfficial ? 'game points' : `${survivors} survivors`;
}

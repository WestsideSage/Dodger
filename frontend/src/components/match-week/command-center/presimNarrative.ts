import type { CommandHistoryRecord, LineupPlayer } from '../../../types';

// Evocative, deterministic season subtitles. These are flavor — they never
// claim a specific narrative outcome, only a season's character.
const SEASON_TITLES = [
  'The Long Season',
  'Proving Ground',
  'A League on Fire',
  'The Climb',
  'No Easy Nights',
  'Chasing the Banner',
  'The Grind Year',
  'The Hungry Year',
  'The Reckoning',
  'Built to Last',
  'Eyes on the Prize',
  'The Hard Way',
];

export function seasonTitle(seasonId: string): string {
  let hash = 0;
  for (let i = 0; i < seasonId.length; i += 1) {
    hash = (hash * 31 + seasonId.charCodeAt(i)) | 0;
  }
  return SEASON_TITLES[Math.abs(hash) % SEASON_TITLES.length];
}

// A short news-clipping recap of the most recent match.
export function bulletinLine(record: CommandHistoryRecord, clubName: string): string {
  const result = record.dashboard.result;
  const opponent = record.dashboard.opponent_name;
  const verb = result === 'Win' ? 'took down' : result === 'Loss' ? 'fell to' : 'split with';
  const lane = record.dashboard.lanes?.[0]?.summary?.trim();
  const lead = `Week ${record.week}: ${clubName} ${verb} ${opponent}.`;
  return lane ? `${lead} ${lane}` : lead;
}

function streak(recentResults: string[]): { kind: 'Win' | 'Loss' | null; length: number } {
  if (recentResults.length === 0) return { kind: null, length: 0 };
  const last = recentResults[recentResults.length - 1];
  if (last !== 'Win' && last !== 'Loss') return { kind: null, length: 0 };
  let length = 0;
  for (let i = recentResults.length - 1; i >= 0; i -= 1) {
    if (recentResults[i] === last) length += 1;
    else break;
  }
  return { kind: last, length };
}

// One sentence on what this match means for the season.
export function stakesLine(
  rank: number | null,
  gamesRemaining: number,
  recentResults: string[],
): string {
  const run = streak(recentResults);
  if (run.kind === 'Loss' && run.length >= 3) {
    return `${run.length} straight losses — a win won't fix everything, but it stops the slide.`;
  }
  if (run.kind === 'Win' && run.length >= 3) {
    return `Riding a ${run.length}-win streak — keep the pressure on and the table will follow.`;
  }
  if (rank === null) {
    return 'A chance to set the tone before the table takes shape.';
  }
  if (rank === 1) {
    return gamesRemaining <= 3
      ? 'Top of the table with the finish line in sight — protect the lead.'
      : 'Top of the table. Every week is now about holding the standard.';
  }
  if (rank <= 3) {
    return 'In the thick of the race — a win here is a statement to the contenders.';
  }
  if (gamesRemaining <= 4) {
    return `Outside the top three with ${gamesRemaining} to play — the margin for error is gone.`;
  }
  return 'Mid-table for now — a win is how the climb starts.';
}

// Highlights the highest-ceiling player on the sheet.
export function playerToWatch(players: LineupPlayer[]): string | null {
  const withPotential = players.filter(player => typeof player.potential === 'number');
  if (withPotential.length === 0) return null;
  const top = withPotential.reduce((best, player) => {
    if (player.potential! > best.potential!) return player;
    if (player.potential === best.potential && (player.age ?? 99) < (best.age ?? 99)) return player;
    return best;
  });
  return `${top.name} carries the highest ceiling on the sheet — reps now shape the climb.`;
}

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

// Where in the season are we? Used so banner copy doesn't claim "thick of
// the race" in week 2 or "finish line in sight" mid-season.
function seasonPhase(week: number | null, gamesRemaining: number): 'opener' | 'early' | 'mid' | 'late' {
  if (week === null || week <= 1) return 'opener';
  if (week <= 2) return 'early';
  if (gamesRemaining <= 2) return 'late';
  return 'mid';
}

// One sentence on what this match means for the season.
export function stakesLine(
  rank: number | null,
  gamesRemaining: number,
  recentResults: string[],
  week: number | null = null,
  playoffStage: string | null = null,
): string {
  // In the playoffs there is no "N regular-season games to play" framing —
  // every match is win-or-go-home, so name the round directly.
  if (playoffStage) {
    // Codex playtest issue 17: "final" is a SUBSTRING of "semifinal", so the
    // semifinal must be checked first or it gets the title-match copy.
    if (/semifinal/i.test(playoffStage)) {
      return 'A Semifinal. Win and the Final is one step away; lose and the season ends here.';
    }
    if (/final/i.test(playoffStage)) {
      return 'The Final. Win it and the banner is yours — there is no next week.';
    }
    return `${playoffStage}. Win or the season ends here.`;
  }
  const run = streak(recentResults);
  if (run.kind === 'Loss' && run.length >= 3) {
    return `${run.length} straight losses — a win won't fix everything, but it stops the slide.`;
  }
  if (run.kind === 'Win' && run.length >= 3) {
    return `Riding a ${run.length}-win streak — keep the pressure on and the table will follow.`;
  }
  const phase = seasonPhase(week, gamesRemaining);
  if (rank === null || phase === 'opener') {
    return 'A chance to set the tone before the table takes shape.';
  }
  if (rank === 1) {
    if (phase === 'late') return 'Top of the table with the finish line in sight — protect the lead.';
    if (phase === 'early') return 'Early lead at the top — too soon to relax, plenty to prove.';
    return 'Top of the table. Every week is now about holding the standard.';
  }
  // Codex playtest issue 16: the playoff line is the TOP FOUR — "outside the
  // top three" told a #4 club (safely in playoff position) it was outside.
  if (rank <= 4) {
    if (phase === 'early') return 'In the playoff places out of the gate — banking points early shapes the seeding race.';
    if (phase === 'late') return 'In playoff position — a win here is a statement to the contenders.';
    return 'In the playoff places — these are the matches that decide seeding.';
  }
  if (phase === 'late') {
    return `Outside the playoff line (top 4) with ${gamesRemaining} to play — the margin for error is gone.`;
  }
  if (phase === 'early') {
    return 'Slow start — time to find an early identity before the table firms up.';
  }
  return 'Mid-table for now — a win is how the climb starts.';
}

// Highlights the develop-target on the sheet: the player with the most
// remaining headroom (ceiling − current OVR), tie-broken by youth.
// Playtest 3 CL-2: the old pick was max CEILING, which flagged tied-top-OVR
// players who grow the LEAST (offseason growth closes a fraction of remaining
// headroom), and "reps now shape the climb" was false for under-23s (they get
// a full practice season whether or not they start — development reps gate).
export function playerToWatch(players: LineupPlayer[]): string | null {
  const withHeadroom = players
    .map(player => ({
      player,
      headroom: typeof player.potential === 'number' ? player.potential - player.overall : null,
    }))
    .filter((entry): entry is { player: LineupPlayer; headroom: number } => entry.headroom !== null);
  if (withHeadroom.length === 0) return null;
  const top = withHeadroom.reduce((best, entry) => {
    if (entry.headroom > best.headroom) return entry;
    if (entry.headroom === best.headroom && (entry.player.age ?? 99) < (best.player.age ?? 99)) return entry;
    return best;
  });
  // A fully-developed sheet has no develop-target — say nothing rather than
  // inventing one.
  if (top.headroom <= 0) return null;
  const room = Math.round(top.headroom);
  // Only under-23s are guaranteed full practice growth on every growth curve;
  // for older players the driver varies, so don't claim one.
  const practiceClause =
    typeof top.player.age === 'number' && top.player.age < 23
      ? ' — young enough to close it in practice, starter or not'
      : '';
  return `${top.player.name} has the most room left on the sheet: ${room} OVR below their ceiling${practiceClause}.`;
}

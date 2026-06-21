import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';
import { formatScoreline } from '../match-week/matchResult';
import { Truncate } from '../../ui';
import styles from './PlayoffBracket.module.css';

function MatchCard({
  match,
  label,
  playerClubId,
}: {
  match: PlayoffBracketMatch;
  label: string;
  playerClubId?: string | null;
}) {
  const played = match.status === 'played';
  // Player outcome on their own played match — a distinct ribbon, not just a
  // highlighted row (Brief 4.6, criterion #3).
  const playerInMatch =
    !!playerClubId && (match.home_club_id === playerClubId || match.away_club_id === playerClubId);
  const playerAdvanced = played && playerInMatch && match.winner_club_id === playerClubId;
  const playerEliminated = played && playerInMatch && match.winner_club_id !== playerClubId;
  const showNote = played && match.decided_by && match.decided_by !== 'regulation' && match.narrative_note;
  // Pick the same scoreline the rest of the app shows: game points for
  // foam/official matches, survivors for legacy. A played foam game has
  // survivors 0-0, which previously rendered as if no game happened.
  const scoreline = played
    ? formatScoreline({
        scoring_model: match.scoring_model ?? undefined,
        home_game_points: match.home_game_points ?? undefined,
        away_game_points: match.away_game_points ?? undefined,
        home_survivors: match.home_survivors ?? 0,
        away_survivors: match.away_survivors ?? 0,
      })
    : null;
  const teamRow = (clubId: string, name: string, value: number | null) => {
    const isWinner = played && match.winner_club_id === clubId;
    return (
      <div key={clubId} className={`${styles.teamRow} ${isWinner ? styles.teamRowWinner : ''}`.trim()}>
        <Truncate className={styles.teamName} title={name}>{name}</Truncate>
        <span className={styles.teamValue}>{value ?? '–'}</span>
      </div>
    );
  };
  const outcomeClass = playerAdvanced
    ? styles.cardOutcomeAdvanced
    : playerEliminated
      ? styles.cardOutcomeEliminated
      : styles.cardNeutral;
  return (
    <div
      data-player-outcome={playerAdvanced ? 'advanced' : playerEliminated ? 'eliminated' : undefined}
      className={`${styles.card} ${outcomeClass}`.trim()}
    >
      <p className={styles.matchLabel}>
        <span>{label}</span>
        {!played && <span className={styles.upcoming}>· upcoming</span>}
        {(playerAdvanced || playerEliminated) && (
          <span className={`${styles.ribbon} ${playerAdvanced ? styles.ribbonAdvanced : styles.ribbonEliminated}`}>
            {playerAdvanced ? 'YOU ADVANCED' : 'YOU ELIMINATED'}
          </span>
        )}
        {played && match.decided_by && match.decided_by !== 'regulation' && (
          <span
            data-testid="playoff-bracket-decided-by-chip"
            data-decided-by={match.decided_by}
            className={styles.decidedChip}
          >
            {match.decided_by === 'overtime' ? 'OT' : 'SEED'}
          </span>
        )}
      </p>
      {teamRow(match.home_club_id, match.home_club_name, scoreline ? scoreline.home.value : null)}
      {teamRow(match.away_club_id, match.away_club_name, scoreline ? scoreline.away.value : null)}
      {/* narrative_note rendered as visible body text, not a title tooltip
          (Brief 4.6, criterion #2). */}
      {showNote && <p className={styles.note}>{match.narrative_note}</p>}
    </div>
  );
}

export function PlayoffBracket({ data }: { data: PlayoffBracketResponse }) {
  if (!data.active) return null;

  const rounds = data.rounds ?? [];
  const semis = rounds.find(round => round.round === 'semifinal')?.matches ?? [];
  const final = rounds.find(round => round.round === 'final')?.matches ?? [];
  const seeds = data.seeds ?? [];

  return (
    <section className={styles.panel} data-testid="playoff-bracket">
      <div className={styles.header}>
        <p className={styles.kicker}>Postseason</p>
        <h2 className={styles.title}>Playoff Bracket</h2>
      </div>

      {seeds.length > 0 && (
        <ol className={styles.seeds} aria-label="Playoff seeds">
          {seeds.map(seed => (
            <li
              key={seed.club_id}
              className={`${styles.seedChip} ${seed.is_player_club ? styles.seedChipUser : ''}`.trim()}
            >
              <b>#{seed.seed}</b> {seed.club_name}
              <em>{seed.wins}-{seed.losses}-{seed.draws}</em>
            </li>
          ))}
        </ol>
      )}

      <div className={styles.grid}>
        <div className={styles.column}>
          <p className={styles.roundLabel}>Semifinals</p>
          {semis.length > 0 ? (
            semis.map((match, index) => (
              <MatchCard key={match.match_id} match={match} label={`Semifinal ${index + 1}`} playerClubId={data.player_club_id} />
            ))
          ) : (
            <p className={styles.empty}>Not yet scheduled.</p>
          )}
        </div>

        <div className={styles.column}>
          <p className={styles.roundLabel}>Championship Final</p>
          {final.length > 0 ? (
            final.map(match => (
              <MatchCard key={match.match_id} match={match} label="Final" playerClubId={data.player_club_id} />
            ))
          ) : (
            <p className={styles.empty}>Awaiting both semifinal winners.</p>
          )}
        </div>

        <div className={styles.column}>
          <p className={styles.roundLabel}>Champion</p>
          {data.champion_club_name ? (
            <div
              className={`${styles.championCard} ${
                data.champion_club_id === data.player_club_id ? styles.championCardUser : ''
              }`.trim()}
            >
              <span className={styles.trophy} aria-hidden="true">🏆</span>
              <strong>{data.champion_club_name}</strong>
              <span>League Champions</span>
            </div>
          ) : (
            <p className={styles.empty}>To be decided in the final.</p>
          )}
        </div>
      </div>
    </section>
  );
}

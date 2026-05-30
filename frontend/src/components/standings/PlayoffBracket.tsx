import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';
import { formatScoreline } from '../match-week/matchResult';

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
      <div
        key={clubId}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '0.5rem',
          padding: '0.4rem 0.6rem',
          background: isWinner ? 'rgba(34,211,238,0.14)' : 'transparent',
          color: isWinner ? '#fff' : '#94a3b8',
          fontWeight: isWinner ? 700 : 500,
          borderRadius: '3px',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
        <span style={{ fontVariantNumeric: 'tabular-nums', color: isWinner ? '#22d3ee' : '#475569' }}>
          {value ?? '–'}
        </span>
      </div>
    );
  };
  const outcomeBorder = playerAdvanced ? '#22c55e' : playerEliminated ? '#f43f5e' : '#1e293b';
  return (
    <div
      data-player-outcome={playerAdvanced ? 'advanced' : playerEliminated ? 'eliminated' : undefined}
      style={{
        border: `1px solid ${outcomeBorder}`,
        borderLeft: playerInMatch && played ? `3px solid ${outcomeBorder}` : `1px solid ${outcomeBorder}`,
        borderRadius: '6px',
        background: 'rgba(2,6,23,0.55)',
        padding: '0.3rem',
        minWidth: '13rem',
      }}
    >
      <p
        className="dm-kicker"
        style={{ margin: '0 0 0.15rem 0.35rem', fontSize: '0.55rem', color: '#475569', display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}
      >
        <span>{label}</span>
        {!played && <span style={{ color: '#f59e0b' }}>· upcoming</span>}
        {(playerAdvanced || playerEliminated) && (
          <span
            style={{
              padding: '0.05rem 0.35rem',
              fontSize: '0.5rem',
              fontWeight: 800,
              letterSpacing: '0.06em',
              color: '#0b1220',
              background: playerAdvanced ? '#22c55e' : '#f43f5e',
              borderRadius: '2px',
            }}
          >
            {playerAdvanced ? 'YOU ADVANCED' : 'YOU ELIMINATED'}
          </span>
        )}
        {played && match.decided_by && match.decided_by !== 'regulation' && (
          <span
            data-testid="playoff-bracket-decided-by-chip"
            data-decided-by={match.decided_by}
            style={{
              padding: '0.05rem 0.3rem',
              fontSize: '0.5rem',
              fontWeight: 700,
              letterSpacing: '0.06em',
              color: '#0b1220',
              background: '#22d3ee',
              borderRadius: '2px',
            }}
          >
            {match.decided_by === 'overtime' ? 'OT' : 'SEED'}
          </span>
        )}
      </p>
      {teamRow(match.home_club_id, match.home_club_name, scoreline ? scoreline.home.value : null)}
      {teamRow(match.away_club_id, match.away_club_name, scoreline ? scoreline.away.value : null)}
      {/* narrative_note rendered as visible body text, not a title tooltip
          (Brief 4.6, criterion #2). */}
      {showNote && (
        <p style={{ margin: '0.3rem 0.35rem 0.15rem', fontSize: '0.62rem', lineHeight: 1.4, color: '#94a3b8' }}>
          {match.narrative_note}
        </p>
      )}
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
    <section className="dm-panel playoff-bracket-panel" data-testid="playoff-bracket">
      <div className="dm-panel-header">
        <p className="dm-kicker">Postseason</p>
        <h2 className="dm-panel-title">Playoff Bracket</h2>
      </div>

      {seeds.length > 0 && (
        <ol className="playoff-bracket-seeds" aria-label="Playoff seeds" style={{ listStyle: 'none', margin: 0 }}>
          {seeds.map(seed => (
            <li
              key={seed.club_id}
              className={`playoff-seed-chip ${seed.is_player_club ? 'is-user' : ''}`}
            >
              <b>#{seed.seed}</b> {seed.club_name}
              <em>{seed.wins}-{seed.losses}-{seed.draws}</em>
            </li>
          ))}
        </ol>
      )}

      <div className="playoff-bracket-grid">
        <div className="playoff-bracket-column">
          <p className="dm-kicker playoff-bracket-round-label">Semifinals</p>
          {semis.length > 0 ? (
            semis.map((match, index) => (
              <MatchCard key={match.match_id} match={match} label={`Semifinal ${index + 1}`} playerClubId={data.player_club_id} />
            ))
          ) : (
            <p className="playoff-bracket-empty">Not yet scheduled.</p>
          )}
        </div>

        <div className="playoff-bracket-column">
          <p className="dm-kicker playoff-bracket-round-label">Championship Final</p>
          {final.length > 0 ? (
            final.map(match => (
              <MatchCard key={match.match_id} match={match} label="Final" playerClubId={data.player_club_id} />
            ))
          ) : (
            <p className="playoff-bracket-empty">Awaiting both semifinal winners.</p>
          )}
        </div>

        <div className="playoff-bracket-column">
          <p className="dm-kicker playoff-bracket-round-label">Champion</p>
          {data.champion_club_name ? (
            <div
              className={`playoff-champion-card ${
                data.champion_club_id === data.player_club_id ? 'is-user' : ''
              }`}
            >
              <span className="playoff-champion-trophy" aria-hidden="true">🏆</span>
              <strong>{data.champion_club_name}</strong>
              <span>League Champions</span>
            </div>
          ) : (
            <p className="playoff-bracket-empty">To be decided in the final.</p>
          )}
        </div>
      </div>
    </section>
  );
}

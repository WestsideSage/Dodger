import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';

function MatchCard({
  match,
  label,
}: {
  match: PlayoffBracketMatch;
  label: string;
}) {
  const played = match.status === 'played';
  const teamRow = (clubId: string, name: string, survivors: number | null) => {
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
          {survivors ?? '–'}
        </span>
      </div>
    );
  };
  return (
    <div
      style={{
        border: '1px solid #1e293b',
        borderRadius: '6px',
        background: 'rgba(2,6,23,0.55)',
        padding: '0.3rem',
        minWidth: '13rem',
      }}
    >
      <p
        className="dm-kicker"
        style={{ margin: '0 0 0.15rem 0.35rem', fontSize: '0.55rem', color: '#475569' }}
      >
        {label}
        {!played && <span style={{ color: '#f59e0b' }}> · upcoming</span>}
      </p>
      {teamRow(match.home_club_id, match.home_club_name, match.home_survivors)}
      {teamRow(match.away_club_id, match.away_club_name, match.away_survivors)}
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
        <div className="playoff-bracket-seeds">
          {seeds.map(seed => (
            <span
              key={seed.club_id}
              className={`playoff-seed-chip ${seed.is_player_club ? 'is-user' : ''}`}
            >
              <b>#{seed.seed}</b> {seed.club_name}
              <em>{seed.wins}-{seed.losses}-{seed.draws}</em>
            </span>
          ))}
        </div>
      )}

      <div className="playoff-bracket-grid">
        <div className="playoff-bracket-column">
          <p className="dm-kicker playoff-bracket-round-label">Semifinals</p>
          {semis.length > 0 ? (
            semis.map((match, index) => (
              <MatchCard key={match.match_id} match={match} label={`Semifinal ${index + 1}`} />
            ))
          ) : (
            <p className="playoff-bracket-empty">Not yet scheduled.</p>
          )}
        </div>

        <div className="playoff-bracket-column">
          <p className="dm-kicker playoff-bracket-round-label">Championship Final</p>
          {final.length > 0 ? (
            final.map(match => (
              <MatchCard key={match.match_id} match={match} label="Final" />
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

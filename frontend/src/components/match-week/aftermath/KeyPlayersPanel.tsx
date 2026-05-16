import type { TopPerformer } from '../../../types';

function StatChips({ player }: { player: TopPerformer }) {
  return (
    <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginTop: '4px', alignItems: 'center' }}>
      {player.eliminations_by_throw > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(249,115,22,0.15)',
            color: '#f97316',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.eliminations_by_throw} Kill{player.eliminations_by_throw !== 1 ? 's' : ''}
        </span>
      )}
      {player.catches_made > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(34,211,238,0.12)',
            color: '#22d3ee',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.catches_made} Catch{player.catches_made !== 1 ? 'es' : ''}
        </span>
      )}
      {player.dodges_successful > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(163,230,53,0.12)',
            color: '#a3e635',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.dodges_successful} Dodge{player.dodges_successful !== 1 ? 's' : ''}
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.6rem',
          color: '#475569',
        }}
      >
        Impact Score {Math.round(player.score)}
      </span>
    </div>
  );
}

export function KeyPlayersPanel({
  performers,
  playerClubName,
}: {
  performers: TopPerformer[];
  playerClubName?: string;
}) {
  if (performers.length === 0) return null;

  return (
    <section className="dm-panel command-key-players" data-testid="key-players-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">Key Performers</p>
      </div>
      <div className="command-key-player-list">
        {performers.slice(0, 3).map((player, index) => {
          const isYours = Boolean(playerClubName && player.club_name === playerClubName);
          const badgeColor = isYours ? '#f97316' : '#334155';

          return (
            <article
              key={player.player_id}
              className="command-key-player"
              style={{ paddingTop: '10px', paddingBottom: '10px' }}
            >
              <span
                className="command-rank-badge"
                style={{ background: badgeColor }}
                aria-label={`Rank ${index + 1}`}
              >
                {index + 1}
              </span>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#f1f5f9' }}>{player.player_name}</strong>
                {isYours ? (
                  <span
                    style={{
                      marginLeft: '0.4rem',
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      background: '#f97316',
                      color: '#000',
                      borderRadius: '3px',
                      padding: '1px 5px',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Your Club
                  </span>
                ) : player.club_name ? (
                  <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
                    {player.club_name}
                  </span>
                ) : null}
                <StatChips player={player} />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

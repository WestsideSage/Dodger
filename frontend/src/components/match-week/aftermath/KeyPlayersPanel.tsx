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
          {player.eliminations_by_throw}K
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
          {player.catches_made}C
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
          {player.dodges_successful}D
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.6rem',
          color: '#475569',
        }}
      >
        {Math.round(player.score)} impact
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
  return (
    <section className="dm-panel command-key-players" data-testid="key-players-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">Key Performers</p>
      </div>
      <div className="command-key-player-list">
        {performers.length === 0 ? (
          <p className="command-empty-copy">Replay stats are loading.</p>
        ) : (
          performers.slice(0, 3).map((player, index) => {
            const isYours = playerClubName
              ? player.club_name === playerClubName
              : false;
            return (
              <article
                key={player.player_id}
                className="command-key-player"
                style={{
                  borderLeft: index === 0
                    ? '2px solid #f97316'
                    : isYours
                    ? '2px solid #22d3ee'
                    : undefined,
                }}
              >
                <span>{index + 1}</span>
                <div>
                  <strong>{player.player_name}</strong>
                  {isYours && (
                    <span className="dm-badge dm-badge-cyan" style={{ marginLeft: '0.4rem', fontSize: '0.6rem' }}>
                      Your Club
                    </span>
                  )}
                  {!isYours && player.club_name && (
                    <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
                      {player.club_name}
                    </span>
                  )}
                  <StatChips player={player} />
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

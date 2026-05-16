import type React from 'react';
import type { TopPerformer } from '../../../types';

function StatChips({ player }: { player: TopPerformer }) {
  const chipStyle = (bg: string, color: string): React.CSSProperties => ({
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '0.55rem',
    background: bg,
    color,
    borderRadius: '3px',
    padding: '1px 4px',
  });

  return (
    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '2px', alignItems: 'center' }}>
      {player.eliminations_by_throw > 0 && (
        <span style={chipStyle('rgba(249,115,22,0.15)', '#f97316')}>
          {player.eliminations_by_throw}K
        </span>
      )}
      {player.catches_made > 0 && (
        <span style={chipStyle('rgba(34,211,238,0.12)', '#22d3ee')}>
          {player.catches_made}C
        </span>
      )}
      {player.dodges_successful > 0 && (
        <span style={chipStyle('rgba(163,230,53,0.12)', '#a3e635')}>
          {player.dodges_successful}D
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.55rem',
          color: '#475569',
        }}
      >
        Imp {Math.round(player.score)}
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
  if (performers.length === 0) {
    return (
      <section className="dm-panel command-key-players" data-testid="key-players-panel">
        <div className="dm-panel-header">
          <p className="dm-kicker">Key Performers</p>
        </div>
        <p className="command-fallout-empty">No standout performances recorded.</p>
      </section>
    );
  }

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
              style={{ paddingTop: '2px', paddingBottom: '2px' }}
            >
              <span
                className="command-rank-badge"
                style={{ background: badgeColor }}
                aria-label={`Rank ${index + 1}`}
              >
                {index + 1}
              </span>
              <div>
                <strong style={{ fontSize: '0.82rem', color: '#f1f5f9' }}>{player.player_name}</strong>
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

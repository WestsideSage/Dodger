import type { TopPerformer } from '../../../types';

function statLine(player: TopPerformer) {
  const stats = [
    player.eliminations_by_throw > 0 ? `${player.eliminations_by_throw} eliminations` : null,
    player.catches_made > 0 ? `${player.catches_made} catches` : null,
    player.dodges_successful > 0 ? `${player.dodges_successful} dodges` : null,
    `${Math.round(player.score)} impact`,
  ].filter(Boolean);

  return stats.join(' / ');
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
                style={isYours ? { borderLeft: '2px solid #22d3ee' } : undefined}
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
                  <p>{statLine(player)}</p>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

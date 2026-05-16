import type { Aftermath } from '../../../types';
import type { ReactNode } from 'react';

function FalloutCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="dm-panel command-fallout-card">
      <p className="dm-kicker" style={{ borderTop: '2px solid #1e293b', paddingTop: '3px' }}>
        {title}
      </p>
      <div className="command-fallout-card-body">{children}</div>
    </article>
  );
}

export function FalloutGrid({
  playerGrowth,
  standingsShift,
  recruitReactions,
}: {
  playerGrowth: Aftermath['player_growth_deltas'];
  standingsShift: Aftermath['standings_shift'];
  recruitReactions: Aftermath['recruit_reactions'];
}) {
  return (
    <section className="command-fallout" data-testid="fallout-grid">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '6px' }}>
        <span className="dm-kicker" style={{ opacity: 0.7 }}>Aftermath</span>
        <span style={{ fontFamily: 'Oswald, sans-serif', fontSize: '0.95rem', fontWeight: 700, color: '#fff', letterSpacing: '0.5px' }}>
          Week Fallout
        </span>
      </div>
      <div className="command-fallout-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <FalloutCard title="Who Grew">
          {playerGrowth.length > 0 ? (
            <ul className="command-clean-list">
              {playerGrowth.slice(0, 4).map((item) => (
                <li key={`${item.player_id}-${item.attribute}`}>
                  <strong>{item.player_name}</strong>
                  <span style={{ color: item.delta > 0 ? '#10b981' : '#f43f5e' }}>
                    {item.attribute} {item.delta > 0 ? '+' : ''}{item.delta}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="command-fallout-empty">No growth logged this week.</p>
          )}
        </FalloutCard>

        <FalloutCard title="Standings Shift">
          {standingsShift.length > 0 ? (
            <>
              <div className="command-fallout-standings-header">
                <span>Club</span>
                <span>Prev → New</span>
              </div>
              <ul className="command-clean-list command-clean-list-compact">
                {standingsShift.slice(0, 3).map((item) => {
                  const moved = item.new_rank - item.old_rank;
                  const up = moved < 0;
                  return (
                    <li key={item.club_id}>
                      <strong>{item.club_name}</strong>
                      <span style={{ color: up ? '#10b981' : '#f43f5e', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem' }}>
                        {up ? '↑' : '↓'} #{item.old_rank} → #{item.new_rank}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="command-empty-copy">No standings changes this week.</p>
          )}
        </FalloutCard>

        <FalloutCard title="Prospect Pulse">
          {recruitReactions.length > 0 ? (
            <ul className="command-clean-list command-clean-list-loose">
              {recruitReactions.slice(0, 3).map((item) => {
                const delta = parseInt(item.interest_delta, 10);
                const isPositive = !isNaN(delta) && delta > 0;
                const isZero = !isNaN(delta) && delta === 0;
                return (
                  <li key={item.prospect_id}>
                    <strong>{item.prospect_name}</strong>
                    <span style={{ color: isPositive ? '#10b981' : isZero ? '#64748b' : '#f43f5e' }}>
                      {item.interest_delta}
                    </span>
                    <small>{item.evidence}</small>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="command-fallout-empty">No prospect movement this week.</p>
          )}
        </FalloutCard>
      </div>
    </section>
  );
}

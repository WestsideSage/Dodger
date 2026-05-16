import type { Aftermath } from '../../../types';
import type { ReactNode } from 'react';

function FalloutCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <article className="dm-panel command-fallout-card">
      <p className="dm-kicker">{title}</p>
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
      <div className="command-section-heading">
        <p className="dm-kicker">Match Fallout</p>
        <h3>What your week caused</h3>
      </div>
      <div className="command-fallout-grid">
        {playerGrowth.length > 0 && (
          <FalloutCard title="Who Grew">
            <ul className="command-clean-list">
              {playerGrowth.slice(0, 4).map((item) => (
                <li key={`${item.player_id}-${item.attribute}`}>
                  <strong>{item.player_name}</strong>
                  <span>{item.attribute} {item.delta > 0 ? '+' : ''}{item.delta}</span>
                </li>
              ))}
            </ul>
          </FalloutCard>
        )}

        {standingsShift.length > 0 && (
          <FalloutCard title="Standings Shift">
            <ul className="command-clean-list">
              {standingsShift.slice(0, 4).map((item) => (
                <li key={item.club_id}>
                  <strong>{item.club_name}</strong>
                  <span>#{item.old_rank} to #{item.new_rank}</span>
                </li>
              ))}
            </ul>
          </FalloutCard>
        )}

        {recruitReactions.length > 0 && (
          <FalloutCard title="Prospect Pulse">
            <ul className="command-clean-list command-clean-list-loose">
              {recruitReactions.slice(0, 3).map((item) => (
                <li key={item.prospect_id}>
                  <strong>{item.prospect_name}</strong>
                  <span>{item.interest_delta}</span>
                  <small>{item.evidence}</small>
                </li>
              ))}
            </ul>
          </FalloutCard>
        )}

        {playerGrowth.length === 0 && standingsShift.length === 0 && recruitReactions.length === 0 && (
          <p className="command-empty-copy" style={{ gridColumn: '1 / -1' }}>No notable fallout from this match.</p>
        )}
      </div>
    </section>
  );
}

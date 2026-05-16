import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  return (
    <section className="dm-panel command-timeline" data-testid="replay-timeline">
      <div className="dm-panel-header">
        <p className="dm-kicker">Match Flow</p>
        <h3 className="dm-panel-title">How it unfolded</h3>
      </div>
      <div className="command-timeline-list">
        {lanes.length === 0 ? (
          <p className="command-empty-copy">No match flow notes were logged.</p>
        ) : (
          lanes.slice(0, 4).map((lane, index) => (
            <article
              key={`${lane.title}-${index}`}
              className="command-timeline-item"
              style={{
                display: 'block',
                borderLeft: `3px solid ${index === 0 ? '#f97316' : '#334155'}`,
                borderRadius: '0 4px 4px 0',
                paddingLeft: '10px',
              }}
            >
              <div>
                <p className="dm-kicker">{lane.title}</p>
                <strong style={{ fontSize: '0.85rem', color: '#f8fafc' }}>{lane.summary}</strong>
                {lane.items.length > 0 && (
                  <ul>
                    {lane.items.slice(0, 3).map((item) => (
                      <li key={item} style={{ color: '#64748b', fontSize: '0.75rem' }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

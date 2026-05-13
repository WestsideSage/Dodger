import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  return (
    <section className="dm-panel command-timeline" data-testid="replay-timeline">
      <div className="dm-panel-header">
        <p className="dm-kicker">Match Flow</p>
        <h3 className="dm-panel-title">Replay identity</h3>
      </div>
      <div className="command-timeline-list">
        {lanes.length === 0 ? (
          <p className="command-empty-copy">No match flow notes were logged.</p>
        ) : (
          lanes.slice(0, 4).map((lane, index) => (
            <article key={`${lane.title}-${index}`} className="command-timeline-item">
              <span className="command-timeline-dot" />
              <div>
                <p className="dm-kicker">{lane.title}</p>
                <strong>{lane.summary}</strong>
                {lane.items.length > 0 && (
                  <ul>
                    {lane.items.slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
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

import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  const beats = lanes.filter((lane) => lane.summary.trim().length > 0);

  if (beats.length === 0) {
    return (
      <section className="dm-panel" data-testid="replay-timeline">
        <div className="command-match-flow-header">
          <p className="dm-kicker">Match Flow</p>
          <h3 className="dm-panel-title">How It Unfolded</h3>
        </div>
        <p className="command-empty-copy">
          No match flow notes were logged.
        </p>
      </section>
    );
  }

  return (
    <section className="dm-panel" data-testid="replay-timeline">
      <div className="command-match-flow-header">
        <p className="dm-kicker">Match Flow</p>
        <h3 className="dm-panel-title">How It Unfolded</h3>
        <span className="command-match-flow-count">
          {beats.length} key moment{beats.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="command-match-flow-scroll-wrap">
        <div
          className="command-match-flow-scroll"
          tabIndex={0}
          aria-label="Match timeline — use arrow keys or scroll to read"
        >
          <ol className="command-match-flow-list">
            {beats.map((lane, i) => (
              <li key={i} className="command-match-flow-event">
                <span className="command-event-badge" aria-hidden="true">
                  {i + 1}
                </span>
                <div>
                  <span className="command-event-phase">{lane.title}</span>
                  <p className="command-event-desc">{lane.summary}</p>
                  {lane.items.length > 0 && (
                    <ul className="command-event-items">
                      {lane.items.map((item, j) => (
                        <li key={j}>{item}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

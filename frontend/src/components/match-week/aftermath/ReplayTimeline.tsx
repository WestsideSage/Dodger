import { useState } from 'react';
import type { CommandDashboardLane } from '../../../types';

function BeatList({ beats }: { beats: CommandDashboardLane[] }) {
  return (
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
  );
}

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  const beats = lanes.filter((lane) => lane.summary.trim().length > 0);
  const [isOpen, setIsOpen] = useState(false);
  const needsScroll = beats.length > 5;

  if (beats.length === 0) {
    return null;
  }

  return (
    <section className="dm-panel" data-testid="replay-timeline" style={{ padding: 0, overflow: 'hidden' }}>
      <button
        className="command-timeline-collapse-bar"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
      >
        <span className="command-timeline-collapse-label">
          <span style={{ color: '#f97316', fontWeight: 700 }}>POSTGAME REPORT</span>
          <span style={{ color: '#475569' }}> · {beats.length} moment{beats.length !== 1 ? 's' : ''}</span>
        </span>
        <span className="command-timeline-collapse-icon" aria-hidden="true">
          {isOpen ? '▲' : '▼'}
        </span>
      </button>

      {isOpen && (
        <div style={{ padding: '0 1rem 1rem' }}>
          {needsScroll ? (
            <div className="command-match-flow-scroll-wrap">
              <div
                className="command-match-flow-scroll"
                tabIndex={0}
                aria-label="Match breakdown — use arrow keys or scroll to read"
              >
                <BeatList beats={beats} />
              </div>
              <p className="command-match-flow-scroll-hint">Scroll for more ↓</p>
            </div>
          ) : (
            <BeatList beats={beats} />
          )}
        </div>
      )}
    </section>
  );
}

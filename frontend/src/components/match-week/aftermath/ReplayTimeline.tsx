import { useState } from 'react';
import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  const [index, setIndex] = useState(0);

  if (lanes.length === 0) {
    return (
      <section className="dm-panel command-timeline" data-testid="replay-timeline">
        <div className="dm-panel-header">
          <p className="dm-kicker">Match Flow</p>
          <h3 className="dm-panel-title">How it unfolded</h3>
        </div>
        <p className="command-empty-copy">No match flow notes were logged.</p>
      </section>
    );
  }

  const lane = lanes[index];
  const total = lanes.length;
  const accentColor = index === 0 ? '#f97316' : '#475569';

  return (
    <section className="dm-panel command-timeline" data-testid="replay-timeline">
      {/* Header row: title left, nav right */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px 8px' }}>
        <div>
          <p className="dm-kicker" style={{ marginBottom: '2px' }}>Match Flow</p>
          <h3 className="dm-panel-title" style={{ margin: 0 }}>How it unfolded</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
            disabled={index === 0}
            aria-label="Previous lane"
            style={{
              background: index === 0 ? 'transparent' : '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: index === 0 ? '#334155' : '#94a3b8',
              width: '32px',
              height: '32px',
              cursor: index === 0 ? 'default' : 'pointer',
              fontSize: '1.1rem',
              lineHeight: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ‹
          </button>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.65rem', color: '#475569', letterSpacing: '1px', minWidth: '28px', textAlign: 'center' }}>
            {index + 1} / {total}
          </span>
          <button
            onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
            disabled={index === total - 1}
            aria-label="Next lane"
            style={{
              background: index === total - 1 ? 'transparent' : '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: index === total - 1 ? '#334155' : '#94a3b8',
              width: '32px',
              height: '32px',
              cursor: index === total - 1 ? 'default' : 'pointer',
              fontSize: '1.1rem',
              lineHeight: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ›
          </button>
        </div>
      </div>

      {/* Lane content */}
      <div style={{ padding: '0 14px 14px' }}>
        <div style={{ borderLeft: `3px solid ${accentColor}`, borderRadius: '0 4px 4px 0', paddingLeft: '12px' }}>
          {/* Phase label */}
          <p
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.55rem',
              letterSpacing: '2px',
              color: accentColor,
              textTransform: 'uppercase',
              margin: '0 0 5px',
              opacity: 0.9,
            }}
          >
            {lane.title}
          </p>

          {/* Summary — main headline */}
          <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9', lineHeight: 1.45, margin: '0 0 8px' }}>
            {lane.summary}
          </p>

          {/* Detail items — clearly separated */}
          {lane.items.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {lane.items.map((item) => (
                <p key={item} style={{ margin: 0, color: '#64748b', fontSize: '0.72rem', lineHeight: 1.5, paddingLeft: '8px', borderLeft: '1px solid #1e293b' }}>
                  {item}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Dot indicators */}
        <div style={{ display: 'flex', gap: '5px', marginTop: '14px', alignItems: 'center' }}>
          {lanes.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              aria-label={`Lane ${i + 1}`}
              style={{
                width: i === index ? '20px' : '6px',
                height: '6px',
                borderRadius: '3px',
                background: i === index ? '#f97316' : '#1e293b',
                border: i === index ? 'none' : '1px solid #334155',
                cursor: 'pointer',
                padding: 0,
                transition: 'width 0.2s, background 0.2s',
              }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

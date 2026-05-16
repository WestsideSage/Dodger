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

  return (
    <section className="dm-panel command-timeline" data-testid="replay-timeline">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px 6px',
        }}
      >
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
              background: 'transparent',
              border: '1px solid #334155',
              borderRadius: '4px',
              color: index === 0 ? '#1e293b' : '#64748b',
              width: '24px',
              height: '24px',
              cursor: index === 0 ? 'default' : 'pointer',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ‹
          </button>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.6rem', color: '#334155', letterSpacing: '1px' }}>
            {index + 1}/{total}
          </span>
          <button
            onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
            disabled={index === total - 1}
            aria-label="Next lane"
            style={{
              background: 'transparent',
              border: '1px solid #334155',
              borderRadius: '4px',
              color: index === total - 1 ? '#1e293b' : '#64748b',
              width: '24px',
              height: '24px',
              cursor: index === total - 1 ? 'default' : 'pointer',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ›
          </button>
        </div>
      </div>

      <div style={{ padding: '0 14px 14px' }}>
        <div
          style={{
            borderLeft: `3px solid ${index === 0 ? '#f97316' : '#334155'}`,
            borderRadius: '0 4px 4px 0',
            paddingLeft: '10px',
          }}
        >
          <p className="dm-kicker" style={{ marginBottom: '4px' }}>{lane.title}</p>
          <strong style={{ fontSize: '0.85rem', color: '#f8fafc', display: 'block', lineHeight: 1.4 }}>
            {lane.summary}
          </strong>
          {lane.items.length > 0 && (
            <ul style={{ margin: '6px 0 0', paddingLeft: '1rem' }}>
              {lane.items.map((item) => (
                <li key={item} style={{ color: '#64748b', fontSize: '0.75rem', lineHeight: 1.5 }}>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Dot indicators */}
        <div style={{ display: 'flex', gap: '4px', marginTop: '12px' }}>
          {lanes.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              aria-label={`Lane ${i + 1}`}
              style={{
                width: i === index ? '16px' : '6px',
                height: '6px',
                borderRadius: '3px',
                background: i === index ? '#f97316' : '#1e293b',
                border: 'none',
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

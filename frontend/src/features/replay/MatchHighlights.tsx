import type { HighlightBeat } from '../../types';

export function MatchHighlights({
  beats,
  onShowInTimeline,
}: {
  beats: HighlightBeat[];
  onShowInTimeline: (eventIndex: number) => void;
}) {
  if (beats.length === 0) {
    return (
      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#475569', textAlign: 'center', padding: 24 }}>
        No highlight package available.
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: '0.7rem' }}>
      {beats.map((beat, index) => (
        <article
          key={`${beat.kind}-${beat.source_event_id}-${index}`}
          data-broadcast-proof-source={beat.proof_source}
          style={{
            border: '1px solid #1e293b',
            borderLeft: `3px solid ${
              beat.kind === 'finish'
                ? '#fbbf24'
                : beat.kind === 'moment'
                  ? '#f97316'
                  : '#22d3ee'
            }`,
            borderRadius: 6,
            padding: '0.8rem 0.9rem',
            background: '#0f172a',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'baseline' }}>
            <div>
              <div style={{ color: '#64748b', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: 1, marginBottom: 4 }}>
                HIGHLIGHT {index + 1}
              </div>
              <div style={{ color: '#f8fafc', fontFamily: 'Oswald, sans-serif', fontSize: 15, letterSpacing: 0.4 }}>
                {beat.title}
              </div>
            </div>
            <div style={{ color: '#475569', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
              TICK {beat.tick}
            </div>
          </div>

          <p style={{ margin: '0.4rem 0 0.7rem', color: '#cbd5e1', fontSize: '0.82rem', lineHeight: 1.5 }}>
            {beat.body}
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => onShowInTimeline(beat.source_event_index)}
              style={{
                background: 'rgba(249,115,22,0.1)',
                color: '#f97316',
                border: '1px solid rgba(249,115,22,0.3)',
                borderRadius: 4,
                padding: '0.35rem 0.55rem',
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                letterSpacing: 1,
              }}
            >
              Show in timeline
            </button>
            <code style={{ color: '#64748b', fontSize: 10 }}>{beat.proof_source}</code>
          </div>
        </article>
      ))}
    </div>
  );
}

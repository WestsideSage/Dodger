export function Headline({
  text,
  week,
  contextLine,
}: {
  text: string;
  week?: number;
  subtitle?: string;
  contextLine?: string;
}) {
  return (
    <div
      style={{
        borderLeft: '3px solid #f97316',
        background: 'linear-gradient(90deg, rgba(249,115,22,0.10) 0%, rgba(249,115,22,0.03) 50%, transparent 100%)',
        borderBottom: '1px solid rgba(249,115,22,0.18)',
        padding: '5px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.55rem',
            letterSpacing: '2.5px',
            color: '#f97316',
            textTransform: 'uppercase' as const,
            opacity: 0.9,
          }}
        >
          War Room
        </span>
        {week !== undefined && (
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.55rem',
              letterSpacing: '1px',
              color: '#64748b',
            }}
          >
            · Wk {week} Debrief
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' as const }}>
        <span
          style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
            fontWeight: 700,
            color: '#fff',
            letterSpacing: '0.5px',
            lineHeight: 1.1,
          }}
        >
          {text}
        </span>
        {contextLine && (
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: '0.72rem',
              color: '#94a3b8',
              lineHeight: 1.4,
              letterSpacing: '0.2px',
            }}
          >
            {contextLine}
          </span>
        )}
      </div>
    </div>
  );
}

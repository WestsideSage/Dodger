export function Headline({
  text,
  week,
  contextLine,
  stage,
  kicker = 'War Room',
  subLabel,
  accent = '#f97316',
}: {
  text: string;
  week?: number;
  subtitle?: string;
  contextLine?: string;
  stage?: string;
  /** Override the mono kicker (e.g. "Bye Week" instead of "War Room"). */
  kicker?: string;
  /** Override the "· Wk N Debrief" sub-label (e.g. "· Rest Report"). */
  subLabel?: string;
  /** Override the orange accent (border / gradient / kicker color). */
  accent?: string;
}) {
  const isPlayoff = Boolean(stage && stage !== 'Regular Season');
  const accentRgb = accent === '#f97316' ? '249,115,22' : accent === '#22d3ee' ? '34,211,238' : '249,115,22';
  return (
    <div
      style={{
        borderLeft: `3px solid ${accent}`,
        background: `linear-gradient(90deg, rgba(${accentRgb},0.10) 0%, rgba(${accentRgb},0.03) 50%, transparent 100%)`,
        borderBottom: `1px solid rgba(${accentRgb},0.18)`,
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
            color: accent,
            textTransform: 'uppercase' as const,
            opacity: 0.9,
          }}
        >
          {kicker}
        </span>
        {(week !== undefined || isPlayoff || subLabel) && (
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.55rem',
              letterSpacing: '1px',
              color: isPlayoff ? '#fbbf24' : '#64748b',
              fontWeight: isPlayoff ? 700 : 400,
            }}
          >
            {subLabel ? `· ${subLabel}` : isPlayoff ? `· ${stage} Debrief` : `· Wk ${week} Debrief`}
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

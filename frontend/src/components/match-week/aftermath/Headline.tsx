export function Headline({
  text,
  week,
  subtitle,
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
        background: 'linear-gradient(110deg, rgba(249,115,22,0.18) 0%, rgba(249,115,22,0.06) 45%, #0f172a 80%)',
        borderBottom: '1px solid rgba(249,115,22,0.25)',
        padding: '18px 20px 16px',
      }}
    >
      {week !== undefined && (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.6rem',
            letterSpacing: '3px',
            color: '#f97316',
            textTransform: 'uppercase' as const,
            marginBottom: '6px',
            opacity: 0.8,
          }}
        >
          Week {week} Result
        </div>
      )}
      <h1
        style={{
          fontFamily: 'Oswald, sans-serif',
          fontSize: 'clamp(1.4rem, 4vw, 2rem)',
          fontWeight: 700,
          color: '#fff',
          letterSpacing: '1px',
          lineHeight: 1.1,
          textShadow: '0 0 30px rgba(249,115,22,0.35)',
          margin: 0,
        }}
      >
        {text}
      </h1>
      {contextLine && (
        <p
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.8rem',
            color: '#94a3b8',
            marginTop: '8px',
            marginBottom: 0,
            lineHeight: 1.5,
            letterSpacing: '0.3px',
          }}
        >
          {contextLine}
        </p>
      )}
      {subtitle && !contextLine && (
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.65rem',
            color: '#94a3b8',
            marginTop: '6px',
            letterSpacing: '0.5px',
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}

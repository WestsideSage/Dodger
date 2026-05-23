export function ComebackCard({ text }: { text: string }) {
  return (
    <article
      data-testid="comeback-card"
      style={{
        padding: '0.95rem 1rem',
        borderRadius: '8px',
        border: '1px solid rgba(16,185,129,0.35)',
        background: 'linear-gradient(135deg, rgba(6,78,59,0.88), rgba(15,23,42,0.95))',
        color: '#d1fae5',
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.64rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#86efac',
        }}
      >
        Comeback
      </p>
      <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', lineHeight: 1.5 }}>
        {text}
      </p>
    </article>
  );
}

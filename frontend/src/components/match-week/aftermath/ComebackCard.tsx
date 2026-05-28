interface NarrativeBeatsLike {
  was_shutout: boolean;
  largest_deficit: number;
}

export function ComebackCard({
  text,
  narrativeBeats,
}: {
  text: string;
  narrativeBeats?: NarrativeBeatsLike;
}) {
  // Task 3 (2026-05-28 playtest-fixes): never render the comeback card
  // on a shutout, or on a match where the player team never trailed.
  // The backend already suppresses the comeback moment in those cases,
  // but the frontend is the last line of defence — if a stale Comeback
  // moment slips through, the card must self-suppress on narrative
  // beats rather than show "clawed it back" on a 3-0 win.
  if (narrativeBeats) {
    if (narrativeBeats.was_shutout) return null;
    if (narrativeBeats.largest_deficit === 0) return null;
  }
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

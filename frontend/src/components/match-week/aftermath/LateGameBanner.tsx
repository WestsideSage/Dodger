export function LateGameBanner({ text }: { text: string }) {
  return (
    <div
      data-testid="late-game-banner"
      style={{
        padding: '0.7rem 0.9rem',
        borderRadius: '6px',
        border: '1px solid rgba(14,165,233,0.35)',
        background: 'linear-gradient(135deg, rgba(8,47,73,0.9), rgba(15,23,42,0.92))',
        color: '#e0f2fe',
        fontWeight: 700,
      }}
    >
      {text}
    </div>
  );
}

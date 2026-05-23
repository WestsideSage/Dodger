export function OneVOneBanner({ text }: { text: string }) {
  return (
    <div
      data-testid="one-v-one-banner"
      style={{
        padding: '0.7rem 0.9rem',
        borderRadius: '6px',
        border: '1px solid rgba(249,115,22,0.45)',
        background: 'linear-gradient(135deg, rgba(67,20,7,0.92), rgba(15,23,42,0.92))',
        color: '#fed7aa',
        fontWeight: 700,
      }}
    >
      {text}
    </div>
  );
}

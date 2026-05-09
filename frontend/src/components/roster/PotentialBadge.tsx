export function PotentialBadge({ tier, confidence }: { tier: string, confidence: number }) {
  const stars = '★'.repeat(confidence) + '☆'.repeat(5 - confidence);
  return (
    <div className="dm-potential-badge" style={{ fontSize: '0.75rem', fontWeight: 600 }}>
      Potential: <span style={{ color: '#22d3ee' }}>{tier}</span> <span style={{ color: 'gold', marginLeft: '0.25rem' }}>{stars}</span>
    </div>
  );
}

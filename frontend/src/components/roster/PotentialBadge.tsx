const TIER_STARS: Record<string, number> = {
  Elite: 5,
  High: 4,
  Mid: 3,
  Low: 2,
  Raw: 1,
};

export function PotentialBadge({ tier, confidence }: { tier: string; confidence: number }) {
  const tierStarCount = TIER_STARS[tier] ?? 3;
  const stars = '★'.repeat(tierStarCount) + '☆'.repeat(5 - tierStarCount);
  const confidencePips = '●'.repeat(confidence) + '○'.repeat(5 - confidence);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.75rem', fontWeight: 600 }}>
      <div>
        <span style={{ color: '#94a3b8' }}>Potential:</span>{' '}
        <span style={{ color: '#22d3ee' }}>{tier}</span>{' '}
        <span style={{ color: '#fbbf24' }}>{stars}</span>
      </div>
      <div>
        <span style={{ color: '#94a3b8' }}>Confidence:</span>{' '}
        <span style={{ color: '#a78bfa' }}>{confidencePips}</span>
      </div>
    </div>
  );
}


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
    <div className="dm-potential-badge" style={{ fontSize: '0.75rem', fontWeight: 600 }}>
      Potential: <span style={{ color: '#22d3ee' }}>{tier}</span>{' '}
      <span style={{ color: 'gold' }}>{stars}</span>{' '}
      <span style={{ color: '#94a3b8', fontSize: '0.625rem' }} title={`Scouting confidence: ${confidence}/5`}>
        {confidencePips}
      </span>
    </div>
  );
}


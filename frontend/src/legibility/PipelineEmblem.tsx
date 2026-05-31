export type PipelineTier = 1 | 2 | 3 | 4 | 5;

const TIER_STYLE: Record<PipelineTier, { color: string; ring: string; name: string }> = {
  5: { color: '#ec4899', ring: 'rgba(236,72,153,0.35)', name: 'Elite' },
  4: { color: '#22d3ee', ring: 'rgba(34,211,238,0.35)', name: 'Premier' },
  3: { color: '#f59e0b', ring: 'rgba(245,158,11,0.35)', name: 'Gold' },
  2: { color: '#cbd5e1', ring: 'rgba(203,213,225,0.30)', name: 'Silver' },
  1: { color: '#b45309', ring: 'rgba(180,83,9,0.30)', name: 'Bronze' },
};

export function PipelineEmblem({ tier, size = 'md' }: { tier: PipelineTier; size?: 'sm' | 'md' }) {
  const t = TIER_STYLE[tier];
  const dim = size === 'sm' ? '1.1rem' : '1.5rem';
  return (
    <span
      role="img"
      aria-label={`Pipeline Tier ${tier} (${t.name})`}
      title={`Pipeline Tier ${tier} — ${t.name}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: dim,
        height: dim,
        borderRadius: '50%',
        color: '#0b1220',
        fontWeight: 800,
        fontSize: size === 'sm' ? '0.6rem' : '0.75rem',
        background: t.color,
        boxShadow: `0 0 0 3px ${t.ring}`,
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {tier}
    </span>
  );
}

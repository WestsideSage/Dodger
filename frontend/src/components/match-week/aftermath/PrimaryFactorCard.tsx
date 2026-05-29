import type { Aftermath } from '../../../types';

const CONFIDENCE_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  high: { label: 'HIGH CONFIDENCE', color: '#10b981', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)' },
  medium: { label: 'LIKELY', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)' },
  low: { label: 'INCONCLUSIVE', color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', border: 'rgba(148,163,184,0.3)' },
};

export function PrimaryFactorCard({ factor }: { factor: NonNullable<Aftermath['primary_factor']> }) {
  const meta = CONFIDENCE_META[factor.confidence] ?? CONFIDENCE_META.low;

  return (
    <div
      data-testid="primary-factor"
      data-factor-code={factor.code}
      style={{
        margin: '12px 0 0',
        padding: '0.7rem 0.85rem',
        background: '#08101f',
        border: '1px solid #1e293b',
        borderLeft: `3px solid ${meta.color}`,
        borderRadius: '4px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
        <span className="dm-kicker" style={{ fontSize: '0.625rem', color: '#64748b' }}>Primary Factor</span>
        <span
          data-testid="primary-factor-confidence"
          style={{
            fontSize: '0.5625rem',
            fontFamily: 'var(--font-mono-data)',
            fontWeight: 900,
            letterSpacing: '0.05em',
            color: meta.color,
            background: meta.bg,
            border: `1px solid ${meta.border}`,
            padding: '0.1rem 0.35rem',
            borderRadius: '3px',
          }}
        >
          {meta.label}
        </span>
      </div>
      <p style={{ margin: '0 0 0.5rem', fontFamily: 'Oswald, sans-serif', fontSize: '0.95rem', color: '#e2e8f0', letterSpacing: '0.3px' }}>
        {factor.title}
      </p>
      <p style={{ margin: 0, color: '#cbd5e1', fontSize: '0.82rem', lineHeight: 1.5 }}>
        {factor.sentence}
      </p>
      {factor.evidence_chips.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.55rem' }}>
          {factor.evidence_chips.map((chip, index) => (
            <span
              key={`${index}-${chip.slice(0, 8)}`}
              data-testid="primary-factor-chip"
              style={{
                fontSize: '0.6875rem',
                fontFamily: 'var(--font-mono-data)',
                color: '#cbd5e1',
                background: '#0f172a',
                border: '1px solid #1e293b',
                padding: '0.15rem 0.45rem',
                borderRadius: '3px',
              }}
            >
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

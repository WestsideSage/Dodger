import type { ReactNode } from 'react';

export type Knowledge = 'known' | 'estimated' | 'hidden';

export function KnownValue({
  state,
  label,
  value,
  hint,
}: {
  state: Knowledge;
  label: string;
  value?: ReactNode;
  hint?: string;
}) {
  const border = state === 'known' ? '1px solid #334155' : state === 'estimated' ? '1px dashed #f59e0b' : '1px dashed #475569';
  return (
    <span
      role="group"
      aria-label={`${label}: ${state === 'hidden' ? 'unknown, scout to reveal' : state}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', border, borderRadius: '4px', padding: '0.1rem 0.4rem' }}
    >
      <span style={{ fontSize: '0.55rem', letterSpacing: '0.05em', color: '#94a3b8', textTransform: 'uppercase' }}>{label}</span>
      <span style={{ fontVariantNumeric: 'tabular-nums', color: state === 'hidden' ? '#64748b' : '#e2e8f0', fontWeight: 700 }}>
        {state === 'hidden' ? '🔒' : value ?? '—'}
      </span>
      {hint && state !== 'known' && (
        <span style={{ fontSize: '0.55rem', color: '#f59e0b' }}>{hint}</span>
      )}
    </span>
  );
}

import type { ReactNode } from 'react';

export function EmptyState({ title, body, icon }: { title: string; body: string; icon?: ReactNode }) {
  return (
    <div
      role="status"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.35rem',
        textAlign: 'center',
        padding: '1.25rem 1rem',
        color: '#94a3b8',
        border: '1px dashed #1e293b',
        borderRadius: '8px',
        background: 'rgba(15,23,42,0.4)',
      }}
    >
      {icon && <span aria-hidden="true" style={{ fontSize: '1.4rem', opacity: 0.7 }}>{icon}</span>}
      <strong style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>{title}</strong>
      <span style={{ fontSize: '0.68rem', lineHeight: 1.4, maxWidth: '22rem' }}>{body}</span>
    </div>
  );
}

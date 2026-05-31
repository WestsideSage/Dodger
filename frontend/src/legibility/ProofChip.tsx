import { useId, useState } from 'react';

export function ProofChip({ label, source }: { label: string; source: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.25rem',
          background: 'rgba(34,211,238,0.10)',
          border: '1px solid rgba(34,211,238,0.4)',
          color: '#67e8f9',
          borderRadius: '3px',
          padding: '0.1rem 0.4rem',
          fontSize: '0.62rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        {label} <span aria-hidden="true">ⓘ</span>
      </button>
      {open && (
        <span
          id={id}
          role="note"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            zIndex: 50,
            width: 'min(15rem, 70vw)',
            background: '#0b1220',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            padding: '0.4rem 0.55rem',
            fontSize: '0.62rem',
            color: '#cbd5e1',
            lineHeight: 1.4,
          }}
        >
          {source}
        </span>
      )}
    </span>
  );
}

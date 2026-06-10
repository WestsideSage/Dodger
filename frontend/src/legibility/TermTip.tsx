import { useId, useState } from 'react';
import { getTerm, type TermId } from './terms';

export function TermTip({ term, children }: { term: TermId; children: React.ReactNode }) {
  const def = getTerm(term);
  const [open, setOpen] = useState(false);
  const descId = useId();

  return (
    <span style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-describedby={open ? descId : undefined}
        aria-label={`What is ${def.label}?`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        // Click must not toggle: hover/focus already set open=true, so a
        // toggle would close the tooltip at the exact moment a mouse user
        // clicks the term to "ask" for it. Click re-opens (touch/AT users);
        // mouse-leave and blur are the closers.
        onClick={() => setOpen(true)}
        onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false); }}
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          margin: 0,
          font: 'inherit',
          color: 'inherit',
          cursor: 'help',
          borderBottom: '1px dotted #64748b',
        }}
      >
        {children}
      </button>
      {open && (
        <span
          id={descId}
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: 0,
            zIndex: 50,
            width: 'min(16rem, 70vw)',
            background: '#0b1220',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            padding: '0.5rem 0.6rem',
            boxShadow: '0 10px 30px -10px rgba(0,0,0,0.6)',
            textAlign: 'left',
            whiteSpace: 'normal',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
            <b style={{ color: '#fff', fontSize: '0.72rem' }}>{def.label}</b>
            <span
              style={{
                fontSize: '0.5rem',
                fontWeight: 800,
                letterSpacing: '0.05em',
                padding: '0.05rem 0.3rem',
                borderRadius: '2px',
                color: '#0b1220',
                background: def.kind === 'mechanical' ? '#22d3ee' : '#a78bfa',
              }}
            >
              {def.kind === 'mechanical' ? 'AFFECTS PLAY' : 'FLAVOR'}
            </span>
          </span>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: '0.66rem', lineHeight: 1.4 }}>
            {def.plain}
          </span>
          <span style={{ display: 'block', color: '#94a3b8', fontSize: '0.62rem', lineHeight: 1.4, marginTop: '0.25rem' }}>
            {def.why}
          </span>
        </span>
      )}
    </span>
  );
}

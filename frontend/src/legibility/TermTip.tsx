import { useId, useState } from 'react';
import { Popover } from '../ui';
import { getTerm, type TermId } from './terms';
import styles from './TermTip.module.css';

export function TermTip({ term, children }: { term: TermId; children: React.ReactNode }) {
  const def = getTerm(term);
  const [open, setOpen] = useState(false);
  const descId = useId();
  const mechanical = def.kind === 'mechanical';

  return (
    <Popover
      open={open}
      id={descId}
      role="tooltip"
      anchor={
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
          // mouse-leave and blur are the closers. This is a TOOLTIP, not a
          // dialog — the portal Popover positions only; it does NOT trap focus.
          onClick={() => setOpen(true)}
          onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false); }}
          className={styles.trigger}
        >
          {children}
        </button>
      }
    >
      <span className={styles.body}>
        <span className={styles.head}>
          <b className={styles.label}>{def.label}</b>
          <span className={`${styles.kind} ${mechanical ? styles.kindMechanical : styles.kindFlavor}`}>
            {mechanical ? 'AFFECTS PLAY' : 'FLAVOR'}
          </span>
        </span>
        <span className={styles.plain}>{def.plain}</span>
        <span className={styles.why}>{def.why}</span>
      </span>
    </Popover>
  );
}

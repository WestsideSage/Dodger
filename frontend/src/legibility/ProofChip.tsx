import { useId, useState } from 'react';
import type { HTMLAttributes } from 'react';
import { Popover } from '../ui';
import styles from './ProofChip.module.css';

interface ProofChipProps extends HTMLAttributes<HTMLButtonElement> {
  label: string;
  source: string;
}

export function ProofChip({ label, source, className = '', ...rest }: ProofChipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <Popover
      open={open}
      role="note"
      id={id}
      anchor={
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((v) => !v)}
          className={`${styles.chip} ${className}`.trim()}
          {...rest}
        >
          {label} <span aria-hidden="true">ⓘ</span>
        </button>
      }
    >
      <span className={styles.note}>{source}</span>
    </Popover>
  );
}

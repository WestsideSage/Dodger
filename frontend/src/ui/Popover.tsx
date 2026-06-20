import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Popover.module.css';

interface PopoverProps extends HTMLAttributes<HTMLDivElement> {
  open: boolean;
  anchor: ReactNode;
  children: ReactNode;
}

export function Popover({ open, anchor, className = '', children, ...rest }: PopoverProps) {
  const anchorRef = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !anchorRef.current || !popRef.current) return;
    const a = anchorRef.current.getBoundingClientRect();
    const p = popRef.current.getBoundingClientRect();
    const margin = 8;
    // default: below + left-aligned; flip up / clamp horizontally if it would overflow
    let top = a.bottom + 6;
    if (top + p.height > window.innerHeight - margin) top = Math.max(margin, a.top - p.height - 6);
    let left = a.left;
    if (left + p.width > window.innerWidth - margin) left = Math.max(margin, window.innerWidth - margin - p.width);
    setPos({ top, left });
  }, [open]);

  return (
    <>
      <span ref={anchorRef} style={{ display: 'inline-flex' }}>{anchor}</span>
      {open && createPortal(
        <div
          ref={popRef}
          className={`${styles.pop} ${className}`.trim()}
          style={{ top: pos.top, left: pos.left }}
          {...rest}
        >
          {children}
        </div>,
        document.body,
      )}
    </>
  );
}

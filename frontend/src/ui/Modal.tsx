import { useEffect, useRef } from 'react';
import type { HTMLAttributes, KeyboardEvent, ReactNode, RefObject } from 'react';
import styles from './Modal.module.css';

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  onClose: () => void;
  children: ReactNode;
  label?: string;
  labelledBy?: string;
  describedBy?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  panelClassName?: string;
}

export function Modal({
  onClose, children, label, labelledBy, describedBy, initialFocusRef,
  className = '', panelClassName = '', ...rest
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const target =
      initialFocusRef?.current ??
      dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE) ??
      dialogRef.current;
    target?.focus?.();
    return () => { previouslyFocused.current?.focus?.(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') { e.stopPropagation(); onClose(); return; }
    if (e.key !== 'Tab') return;
    const f = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
    if (!f || f.length === 0) { e.preventDefault(); dialogRef.current?.focus(); return; }
    const first = f[0], last = f[f.length - 1], active = document.activeElement;
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  };

  return (
    <div className={`${styles.overlay} ${className}`.trim()} role="presentation" onClick={onClose} {...rest}>
      <div
        ref={dialogRef}
        className={`${styles.panel} ${panelClassName}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={labelledBy ? undefined : label}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        {children}
      </div>
    </div>
  );
}

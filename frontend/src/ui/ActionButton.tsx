import type { ReactNode } from 'react';
import type React from 'react';
import styles from './ActionButton.module.css';

export function ActionButton({
  children,
  variant = 'secondary',
  className = '',
  style,
  type,
  ...props
}: {
  children: ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost';
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  // Visual treatment lives in the .dm-action / .dm-action-<variant> CSS (index.css).
  // The module class adds token-driven layout; both class sets coexist until P8.
  return (
    <button
      {...props}
      type={type ?? 'button'}
      className={`dm-action dm-action-${variant} ${styles.btn} ${className}`.trim()}
      style={style}
    >
      {children}
    </button>
  );
}

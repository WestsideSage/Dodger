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
  // Self-contained Floodlight: layout + the full 5-color-contract color
  // treatment for every variant live in ActionButton.module.css. No legacy
  // .dm-action* class is rendered — color no longer leaks from index.css.
  return (
    <button
      {...props}
      type={type ?? 'button'}
      className={`${styles.btn} ${styles[variant]} ${className}`.trim()}
      style={style}
    >
      {children}
    </button>
  );
}

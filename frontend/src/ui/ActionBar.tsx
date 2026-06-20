import type { HTMLAttributes, ReactNode } from 'react';
import styles from './ActionBar.module.css';

interface ActionBarProps extends HTMLAttributes<HTMLDivElement> { children: ReactNode; }

export function ActionBar({ className = '', children, ...rest }: ActionBarProps) {
  return <div className={`${styles.bar} ${className}`.trim()} {...rest}>{children}</div>;
}

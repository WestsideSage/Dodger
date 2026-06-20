import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Tag.module.css';

export type TagTone = 'live' | 'verified' | 'talent' | 'out' | 'neutral';

interface TagProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: TagTone;
  children: ReactNode;
}

export function Tag({ tone = 'neutral', className = '', children, ...rest }: TagProps) {
  return <span className={`${styles.tag} ${styles[tone]} ${className}`.trim()} {...rest}>{children}</span>;
}

import type { ElementType, HTMLAttributes, ReactNode } from 'react';
import styles from './Surface.module.css';

interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: 0 | 1 | 2;
  as?: ElementType;
  children: ReactNode;
}

export function Surface({ elevation = 1, as: Tag = 'div', className = '', children, ...rest }: SurfaceProps) {
  return (
    <Tag className={`${styles.surface} ${styles['e' + elevation]} ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}

export function Card({ className = '', children, ...rest }: SurfaceProps) {
  return <Surface className={`${styles.card} ${className}`.trim()} {...rest}>{children}</Surface>;
}

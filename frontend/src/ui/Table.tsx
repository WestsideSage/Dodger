import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Table.module.css';

interface TableProps extends HTMLAttributes<HTMLTableElement> {
  density?: 'comfortable' | 'compact';
  children: ReactNode;
}

export function Table({ density = 'comfortable', className = '', children, ...rest }: TableProps) {
  return (
    <div className={styles.wrap}>
      <table className={`${styles.t} ${styles[density]} ${className}`.trim()} {...rest}>{children}</table>
    </div>
  );
}

import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';
import styles from './Grid.module.css';

interface GridProps extends HTMLAttributes<HTMLDivElement> {
  min?: string;
  gap?: string;
  children: ReactNode;
}

export function Grid({ min, gap, className = '', style, children, ...rest }: GridProps) {
  const vars = { ...(min ? { '--grid-min': min } : {}), ...(gap ? { '--grid-gap': gap } : {}) } as CSSProperties;
  return (
    <div className={`${styles.grid} ${className}`.trim()} style={{ ...vars, ...style }} {...rest}>
      {children}
    </div>
  );
}

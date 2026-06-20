import type { HTMLAttributes, ReactNode } from 'react';
import styles from './ScrollRegion.module.css';

interface ScrollRegionProps extends HTMLAttributes<HTMLDivElement> {
  /** Constrain height here OR let a flex parent constrain it; never both nested. */
  maxHeight?: string;
  children: ReactNode;
}

export function ScrollRegion({ maxHeight, className = '', style, children, ...rest }: ScrollRegionProps) {
  return (
    <div className={`${styles.scroll} ${className}`.trim()} style={{ maxHeight, ...style }} {...rest}>
      {children}
    </div>
  );
}

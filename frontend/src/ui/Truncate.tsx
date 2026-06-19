import type { ElementType, HTMLAttributes, ReactNode } from 'react';
import styles from './Truncate.module.css';

interface TruncateProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  children: ReactNode;
}

export function Truncate({ as: Tag = 'span', className = '', children, ...rest }: TruncateProps) {
  return <Tag className={`${styles.truncate} ${className}`.trim()} {...rest}>{children}</Tag>;
}

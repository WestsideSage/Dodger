import type { HTMLAttributes } from 'react';
import styles from './RecordCell.module.css';

interface RecordCellProps extends HTMLAttributes<HTMLSpanElement> {
  wins: number;
  losses: number;
  draws?: number;
}

export function RecordCell({ wins, losses, draws, className = '', ...rest }: RecordCellProps) {
  const text = draws != null ? `${wins}–${losses}–${draws}` : `${wins}–${losses}`;
  return <span className={`${styles.record} ${className}`.trim()} {...rest}>{text}</span>;
}

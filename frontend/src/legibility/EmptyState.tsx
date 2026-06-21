import type { ReactNode } from 'react';
import styles from './EmptyState.module.css';

export function EmptyState({ title, body, icon }: { title: string; body: string; icon?: ReactNode }) {
  return (
    <div role="status" className={styles.box}>
      {icon && (
        <span aria-hidden="true" className={styles.icon}>
          {icon}
        </span>
      )}
      <strong className={styles.title}>{title}</strong>
      <span className={styles.body}>{body}</span>
    </div>
  );
}

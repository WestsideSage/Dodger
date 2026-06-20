import type { ReactNode } from 'react';
import styles from './PageHeader.module.css';

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  stats,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  stats?: ReactNode;
}) {
  return (
    <div className={styles.header}>
      {eyebrow && <p className={`dm-kicker ${styles.eyebrow}`}>{eyebrow}</p>}
      <div className={styles.row}>
        <div className={styles.titleGroup}>
          <h2 className={`dm-panel-title ${styles.title}`}>{title}</h2>
          {description && <p className={`dm-panel-subtitle ${styles.description}`}>{description}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      {stats && <div className={styles.stats}>{stats}</div>}
    </div>
  );
}

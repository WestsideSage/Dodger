import type { ReactNode } from 'react';
import styles from './StatusMessage.module.css';

export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export function StatusMessage({
  title,
  children,
  tone = 'info',
  role,
}: {
  title: string;
  children?: ReactNode;
  tone?: Tone;
  role?: 'status' | 'alert';
}) {
  const resolvedRole: 'status' | 'alert' =
    role ?? (tone === 'danger' || tone === 'warning' ? 'alert' : 'status');
  const ariaLive: 'assertive' | 'polite' = resolvedRole === 'alert' ? 'assertive' : 'polite';
  return (
    <div
      role={resolvedRole}
      aria-live={ariaLive}
      className={`${styles.box} ${styles['tone-' + tone]}`.trim()}
    >
      <div className={styles.kicker}>{title}</div>
      {children && <div className={styles.body}>{children}</div>}
    </div>
  );
}

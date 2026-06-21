import styles from './SimTransition.module.css';

export function SimTransition() {
  return (
    <div className={styles.overlay} aria-live="polite" aria-busy="true">
      <div className={styles.spinner} />
      <p className={styles.label}>Simulating...</p>
    </div>
  );
}

import styles from './aftermathCards.module.css';

export function LateGameBanner({ text }: { text: string }) {
  return (
    <div data-testid="late-game-banner" className={styles.banner}>
      {text}
    </div>
  );
}

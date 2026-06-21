import styles from './aftermathCards.module.css';

export function OneVOneBanner({ text }: { text: string }) {
  return (
    <div data-testid="one-v-one-banner" className={`${styles.banner} ${styles.bannerVolt}`}>
      {text}
    </div>
  );
}

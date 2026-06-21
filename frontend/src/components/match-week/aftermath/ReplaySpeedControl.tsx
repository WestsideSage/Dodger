import styles from './aftermathCards.module.css';

export type ReplaySpeed = '1x' | '2x' | '4x' | 'instant';

const SPEEDS: ReplaySpeed[] = ['1x', '2x', '4x', 'instant'];

export function ReplaySpeedControl({
  speed,
  onChange,
}: {
  speed: ReplaySpeed;
  onChange: (speed: ReplaySpeed) => void;
}) {
  return (
    <div data-testid="replay-speed-control" className={styles.speed}>
      {SPEEDS.map((value) => {
        const selected = value === speed;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            className={`${styles.speedBtn}${value === 'instant' ? ` ${styles.speedBtnWide}` : ''}${selected ? ` ${styles.speedBtnActive}` : ''}`}
          >
            {value}
          </button>
        );
      })}
    </div>
  );
}

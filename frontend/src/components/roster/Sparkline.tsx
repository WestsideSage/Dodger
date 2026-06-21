import styles from './Sparkline.module.css';

export function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return <div className={styles.fallback} />;
  
  const min = Math.min(...data) - 1;
  const max = Math.max(...data) + 1;
  const range = max - min;
  const width = 60;
  const height = 20;
  
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke="var(--volt2)"
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
}

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
    <div
      data-testid="replay-speed-control"
      style={{
        display: 'inline-flex',
        gap: '0.35rem',
        padding: '0.25rem',
        borderRadius: '999px',
        background: '#0f172a',
        border: '1px solid #1e293b',
      }}
    >
      {SPEEDS.map((value) => {
        const selected = value === speed;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            style={{
              minWidth: value === 'instant' ? '4.6rem' : '2.6rem',
              padding: '0.35rem 0.65rem',
              borderRadius: '999px',
              border: selected ? '1px solid #f97316' : '1px solid transparent',
              background: selected ? 'rgba(249,115,22,0.18)' : 'transparent',
              color: selected ? '#fde68a' : '#94a3b8',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.68rem',
              cursor: 'pointer',
            }}
          >
            {value}
          </button>
        );
      })}
    </div>
  );
}

export function AftermathActionBar({
  onAdvance,
  onViewReplay,
  matchId,
  isAdvancing = false,
}: {
  onAdvance: () => void;
  onViewReplay?: () => void;
  matchId?: string;
  isAdvancing?: boolean;
}) {
  const hasReplay = Boolean(matchId && onViewReplay);

  return (
    <div
      style={{ padding: '12px 16px', display: 'flex', gap: '8px', alignItems: 'stretch' }}
      data-testid="after-action-bar"
    >
      {hasReplay && (
        <button
          onClick={onViewReplay}
          style={{
            background: 'transparent',
            border: '1px solid #475569',
            borderRadius: '8px',
            color: '#94a3b8',
            padding: '10px 18px',
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.75rem',
            letterSpacing: '1px',
            cursor: 'pointer',
            whiteSpace: 'nowrap' as const,
          }}
        >
          WATCH REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        style={{
          flex: 1,
          background: isAdvancing ? '#7c3d12' : '#f97316',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          padding: '10px 16px',
          fontFamily: 'Oswald, sans-serif',
          fontSize: '0.85rem',
          letterSpacing: '2px',
          cursor: isAdvancing ? 'default' : 'pointer',
        }}
      >
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
    </div>
  );
}

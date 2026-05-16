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
  return (
    <div style={{ padding: '12px' }} data-testid="after-action-bar">
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        style={{
          width: '100%',
          background: isAdvancing ? '#7c3d12' : '#f97316',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          padding: '12px',
          fontFamily: 'Oswald, sans-serif',
          fontSize: '0.9rem',
          letterSpacing: '2px',
          cursor: isAdvancing ? 'default' : 'pointer',
          boxShadow: isAdvancing ? 'none' : '0 0 20px rgba(249,115,22,0.2)',
        }}
      >
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
      {matchId && onViewReplay && (
        <button
          onClick={onViewReplay}
          style={{
            width: '100%',
            background: 'transparent',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#64748b',
            padding: '8px',
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.75rem',
            letterSpacing: '1px',
            cursor: 'pointer',
            marginTop: '6px',
          }}
        >
          WATCH REPLAY
        </button>
      )}
    </div>
  );
}

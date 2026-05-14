import type { OffseasonBeat } from '../../types';

type DevelopmentBeat = Extract<OffseasonBeat, { key: 'development' }>;

export function DevelopmentResults({
    beat,
    onComplete,
    acting,
}: {
    beat: DevelopmentBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const players = beat.payload.players;

    return (
        <section className="command-offseason-shell" data-testid="offseason-development">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    OFFSEASON DEVELOPMENT
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.25rem' }}>
                    Your Roster Progress
                </h2>
                <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    {players.length} player{players.length !== 1 ? 's' : ''} on your roster
                </p>
            </div>

            <div className="dm-panel" style={{ padding: '0', overflow: 'hidden' }}>
                {players.length === 0 ? (
                    <p style={{ padding: '1rem', color: '#64748b', textAlign: 'center' }}>
                        No development data available for your roster.
                    </p>
                ) : (
                    players.map((player, i) => {
                        const improved = player.delta > 0;
                        const declined = player.delta < 0;
                        const deltaColor = improved ? '#10b981' : declined ? '#ef4444' : '#64748b';
                        const deltaLabel = player.delta > 0 ? `+${player.delta}` : `${player.delta}`;

                        return (
                            <div
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    padding: '0.65rem 1rem',
                                    borderBottom: '1px solid #0f172a',
                                    gap: '1rem',
                                }}
                            >
                                <span style={{ flex: 1, color: '#e2e8f0', fontSize: '0.9rem', fontWeight: 500 }}>
                                    {player.name}
                                </span>
                                <span style={{ color: '#64748b', fontSize: '0.8rem', fontVariantNumeric: 'tabular-nums' }}>
                                    {player.ovr_before} → {player.ovr_after}
                                </span>
                                <span
                                    style={{
                                        minWidth: '2.5rem',
                                        textAlign: 'right',
                                        fontWeight: 700,
                                        fontSize: '0.85rem',
                                        color: deltaColor,
                                        fontVariantNumeric: 'tabular-nums',
                                    }}
                                >
                                    {deltaLabel}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <button
                        className="dm-btn dm-btn-primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </button>
                </div>
            </div>
        </section>
    );
}

import type { OffseasonBeat } from '../../types';
import { ActionButton } from '../ui';

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
    const players = beat.payload.players.filter(p => p.delta !== 0);

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
                    {players.length} player{players.length !== 1 ? 's' : ''} changed OVR
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

                        const ovrDisplay = `${Math.round(player.ovr_before)} → ${Math.round(player.ovr_after)}`;

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
                                    {ovrDisplay}
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

            <div style={{
                background: 'rgba(34, 211, 238, 0.05)',
                border: '1px solid rgba(34, 211, 238, 0.15)',
                borderRadius: '8px',
                padding: '1.25rem',
                margin: '1.5rem 0 0 0',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
            }}>
                <div style={{ fontSize: '2rem' }} aria-hidden="true">⏳</div>
                <div>
                  <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc' }}>
                    League Transition Checklist Completed
                  </h4>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
                    • <strong>Aging:</strong> All active players aged by 1 year. <br />
                    • <strong>Conditioning:</strong> Match fatigue has been fully reset. <br />
                    • <strong>Roster Stabilization:</strong> Offseason development and skill regression applied.
                  </p>
                </div>
            </div>

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton
                        variant="primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
}

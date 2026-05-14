import type { OffseasonBeat } from '../../types';

type RecapBeat = Extract<OffseasonBeat, { key: 'recap' }>;

export function RecapStandings({
    beat,
    onComplete,
    acting,
}: {
    beat: RecapBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const standings = beat.payload.standings;

    return (
        <section className="command-offseason-shell" data-testid="offseason-recap">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    FINAL STANDINGS
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '1rem' }}>
                    Season Table
                </h2>
            </div>

            <div className="dm-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                        gap: '0 0.75rem',
                        padding: '0.5rem 1rem',
                        borderBottom: '1px solid #1e293b',
                        fontSize: '0.65rem',
                        color: '#475569',
                        letterSpacing: '0.06em',
                    }}
                >
                    <span>#</span>
                    <span>Club</span>
                    <span style={{ textAlign: 'center' }}>W-L-D</span>
                    <span style={{ textAlign: 'right' }}>Pts</span>
                    <span style={{ textAlign: 'right' }}>Diff</span>
                </div>

                {standings.map((row) => (
                    <div
                        key={row.rank}
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                            gap: '0 0.75rem',
                            padding: '0.6rem 1rem',
                            borderLeft: row.is_player_club ? '3px solid #f97316' : '3px solid transparent',
                            borderBottom: '1px solid #0f172a',
                            background: row.is_player_club ? '#1c1009' : 'transparent',
                            color: row.is_player_club ? '#fb923c' : '#94a3b8',
                            fontSize: '0.85rem',
                            alignItems: 'center',
                        }}
                    >
                        <span style={{ color: '#475569', fontSize: '0.75rem' }}>{row.rank}</span>
                        <span style={{ fontWeight: row.is_player_club ? 700 : 400, color: row.is_player_club ? '#fb923c' : '#e2e8f0' }}>
                            {row.club_name}
                        </span>
                        <span style={{ textAlign: 'center', color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                            {row.wins}-{row.losses}-{row.draws}
                        </span>
                        <span style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#e2e8f0' }}>
                            {row.points}
                        </span>
                        <span
                            style={{
                                textAlign: 'right',
                                fontVariantNumeric: 'tabular-nums',
                                color: row.diff > 0 ? '#10b981' : row.diff < 0 ? '#ef4444' : '#64748b',
                            }}
                        >
                            {row.diff > 0 ? '+' : ''}{row.diff}
                        </span>
                    </div>
                ))}
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

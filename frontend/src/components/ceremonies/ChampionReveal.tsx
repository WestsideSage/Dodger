import type { OffseasonBeat } from '../../types';

type ChampionBeat = Extract<OffseasonBeat, { key: 'champion' }>;

export function ChampionReveal({
    beat,
    onComplete,
    acting,
}: {
    beat: ChampionBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const champion = beat.payload.champion;

    return (
        <section className="command-offseason-shell" data-testid="offseason-champion">
            <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    SEASON CHAMPION
                </p>
                {champion ? (
                    <>
                        <h2
                            style={{
                                fontSize: '2rem',
                                fontWeight: 800,
                                color: '#fbbf24',
                                marginBottom: '1rem',
                                lineHeight: 1.2,
                            }}
                        >
                            {champion.club_name}
                        </h2>
                        <div
                            style={{
                                display: 'flex',
                                gap: '1.5rem',
                                justifyContent: 'center',
                                flexWrap: 'wrap',
                                marginBottom: '1.5rem',
                            }}
                        >
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#e2e8f0' }}>
                                    {champion.wins}-{champion.losses}-{champion.draws}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Record</div>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fbbf24' }}>
                                    {champion.title_count}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                    {champion.title_count === 1 ? 'Title' : 'Titles'}
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    <p style={{ color: '#94a3b8', fontSize: '1rem', marginBottom: '1.5rem' }}>
                        {typeof beat.body === 'string' ? beat.body : 'No champion determined this season.'}
                    </p>
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

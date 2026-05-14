import type { OffseasonBeat } from '../../types';
import { ActionButton } from '../ui';

type RookieClassPreviewBeat = Extract<OffseasonBeat, { key: 'rookie_class_preview' }>;

export function RookieClassPreview({
    beat,
    onComplete,
    acting,
}: {
    beat: RookieClassPreviewBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const { class_size, top_prospects, free_agents, archetypes, storylines } = beat.payload;

    return (
        <section className="command-offseason-shell" data-testid="offseason-rookie-preview">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    INCOMING CLASS
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '1rem' }}>
                    Rookie Class Preview
                </h2>
            </div>

            <div className="dm-panel" style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', padding: '1rem' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#e2e8f0' }}>{class_size}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Incoming Rookies</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: top_prospects > 0 ? '#10b981' : '#64748b' }}>{top_prospects}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Top Prospects (70+ OVR)</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#94a3b8' }}>{free_agents}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Veteran Free Agents</div>
                </div>
            </div>

            {archetypes.length > 0 && (
                <div className="dm-panel" style={{ padding: '0.75rem 1rem' }}>
                    <p className="dm-kicker">Archetype Breakdown</p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {archetypes.map((a) => (
                            <span
                                key={a.name}
                                style={{
                                    background: '#1e293b',
                                    borderRadius: '4px',
                                    padding: '0.2rem 0.5rem',
                                    fontSize: '0.75rem',
                                    color: '#94a3b8',
                                }}
                            >
                                {a.name} ({a.count})
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {storylines.length > 0 && (
                <div className="dm-panel" style={{ padding: '0.75rem 1rem' }}>
                    <p className="dm-kicker">Market Storylines</p>
                    <ul style={{ margin: '0.5rem 0 0', padding: '0 0 0 1.1rem', color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6 }}>
                        {storylines.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to Signing Day.</p>
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

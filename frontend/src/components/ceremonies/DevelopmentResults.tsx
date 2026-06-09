import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../ui';
import { TermTip } from '../../legibility';

type DevelopmentBeat = Extract<OffseasonBeat, { key: 'development' }>;

const _ATTR_LABEL: Record<string, string> = {
    accuracy: 'ACC',
    power: 'POW',
    dodge: 'DOD',
    catch: 'CAT',
    stamina: 'STA',
    tactical_iq: 'IQ',
    catch_courage: 'CC',
    throw_selection_iq: 'TIQ',
    conditioning_curve: 'CON',
};

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
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · Development`}
                title="Your Roster Progress"
                description={`${players.length} player${players.length !== 1 ? 's' : ''} changed OVR`}
                stats={
                    <div className="command-offseason-progress" aria-label="Offseason beat progress">
                        {Array.from({ length: beat.total_beats }).map((_, index) => (
                            <span
                                key={index}
                                className={
                                    index <= beat.beat_index
                                        ? 'command-offseason-progress-step command-offseason-progress-step-active'
                                        : 'command-offseason-progress-step'
                                }
                            />
                        ))}
                    </div>
                }
            />

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

                        const movedAttrs = player.attr_deltas
                            ? Object.entries(player.attr_deltas).filter(([, v]) => v !== 0)
                            : [];

                        return (
                            <div
                                key={i}
                                style={{
                                    padding: '0.65rem 1rem',
                                    borderBottom: '1px solid #0f172a',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '0.25rem' }}>
                                        <span style={{ color: '#e2e8f0', fontSize: '0.9rem', fontWeight: 500 }}>
                                            {player.name}
                                        </span>
                                        {player.potential_ceiling != null && (
                                            <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
                                                <TermTip term="growth.ceiling">Ceiling</TermTip>{' '}{player.potential_ceiling}
                                            </span>
                                        )}
                                        {player.notes && player.notes.length > 0 && (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                                {player.notes.map((note: string, idx: number) => (
                                                    <span key={idx} style={{ color: '#fbbf24', fontSize: '0.75rem', fontStyle: 'italic' }}>
                                                        ✨ {note}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
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
                                {movedAttrs.length > 0 && (
                                    <div style={{
                                        display: 'flex',
                                        flexWrap: 'wrap',
                                        gap: '0.3rem 0.6rem',
                                        marginTop: '0.4rem',
                                        paddingLeft: '0',
                                    }}>
                                        {movedAttrs.map(([attr, val]) => {
                                            const attrColor = val > 0 ? '#10b981' : '#ef4444';
                                            const label = _ATTR_LABEL[attr] ?? attr;
                                            const termId =
                                                attr === 'throw_selection_iq' ? 'attr.throw_selection_iq' as const
                                                : attr === 'catch_courage' ? 'attr.catch_courage' as const
                                                : null;
                                            return (
                                                <span
                                                    key={attr}
                                                    style={{
                                                        fontSize: '0.7rem',
                                                        color: '#94a3b8',
                                                        fontVariantNumeric: 'tabular-nums',
                                                    }}
                                                >
                                                    {termId ? (
                                                        <TermTip term={termId}>{label}</TermTip>
                                                    ) : (
                                                        label
                                                    )}{' '}
                                                    <span style={{ color: attrColor, fontWeight: 600 }}>
                                                        {val > 0 ? `+${val}` : `${val}`}
                                                    </span>
                                                </span>
                                            );
                                        })}
                                    </div>
                                )}
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

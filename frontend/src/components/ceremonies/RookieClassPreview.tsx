import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../ui';

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

    const hasTopProspects = top_prospects > 0;
    const qualityPct = class_size > 0 ? Math.round((top_prospects / class_size) * 100) : 0;
    const maxArchetype = archetypes.reduce((m, a) => Math.max(m, a.count), 0);

    return (
        <section className="command-offseason-shell" data-testid="offseason-rookie-preview">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · Incoming Class`}
                title="Rookie Class Preview"
                description="Scouting reports are in. Here is the talent entering the league before you set your board."
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

            {/* Primary signal: class quality. top_prospects is the single number
                that should drive how aggressively the player spends slots
                (Brief 4.5, criterion #1). */}
            <div
                className="dm-panel"
                style={{
                    padding: '1.1rem 1.15rem',
                    borderLeft: `3px solid ${hasTopProspects ? '#10b981' : '#475569'}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1.1rem',
                }}
            >
                <div style={{ flex: '0 0 auto', textAlign: 'center', minWidth: '4.5rem' }}>
                    <div style={{ fontSize: '3rem', lineHeight: 1, fontWeight: 900, color: hasTopProspects ? '#10b981' : '#64748b' }}>
                        {top_prospects}
                    </div>
                    <div style={{ fontSize: '0.62rem', fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#64748b', marginTop: '0.2rem' }}>
                        Top Prospects
                    </div>
                </div>
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                    <p style={{ margin: 0, color: '#e2e8f0', fontWeight: 700, fontSize: '0.9rem' }}>
                        {hasTopProspects
                            ? `${top_prospects} of ${class_size} rookies project at 70+ OVR`
                            : 'No rookies project at 70+ OVR this year'}
                    </p>
                    {/* Explainer rendered as visible text on all devices — was a
                        hover-only title attribute (Brief 4.5, criterion #3). */}
                    <p style={{ margin: '0.3rem 0 0', color: '#94a3b8', fontSize: '0.76rem', lineHeight: 1.5 }}>
                        A 70+ scouted floor means scouts are already confident in the player — a strong class rewards spending your signing slots aggressively.
                    </p>
                    {class_size > 0 && (
                        <div style={{ marginTop: '0.55rem' }} aria-hidden="true">
                            <div style={{ height: '5px', borderRadius: '999px', background: '#1e293b', overflow: 'hidden' }}>
                                <div style={{ width: `${qualityPct}%`, height: '100%', background: hasTopProspects ? '#10b981' : '#475569' }} />
                            </div>
                            <span style={{ fontSize: '0.66rem', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' }}>
                                {qualityPct}% high-confidence
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Secondary: class composition. class_size headlines; free_agents
                demoted to an inline footnote (Brief 4.5, criterion #2). */}
            <div className="dm-panel" style={{ padding: '0.85rem 1rem' }}>
                <dl style={{ display: 'flex', alignItems: 'baseline', gap: '1.5rem', margin: 0, flexWrap: 'wrap' }}>
                    <div>
                        <dd style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800, color: '#f1f5f9' }}>{class_size}</dd>
                        <dt style={{ fontSize: '0.66rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#64748b' }}>Incoming Rookies</dt>
                    </div>
                    <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                        <dt style={{ fontSize: '0.66rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#64748b' }}>Veteran Free Agents</dt>
                        <dd style={{ margin: '0.1rem 0 0', fontSize: '0.9rem', fontWeight: 700, color: '#94a3b8' }}>{free_agents} also available</dd>
                    </div>
                </dl>

                {archetypes.length > 0 && (
                    <div style={{ marginTop: '0.9rem', borderTop: '1px solid #1e293b', paddingTop: '0.75rem' }}>
                        <p className="dm-kicker" style={{ margin: '0 0 0.5rem' }}>Archetype Breakdown</p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                            {archetypes.map((a) => (
                                <div key={a.name} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                    <span style={{ flex: '0 0 7rem', fontSize: '0.76rem', color: '#cbd5e1' }}>{a.name}</span>
                                    <div style={{ flex: '1 1 auto', height: '8px', borderRadius: '999px', background: '#0a1220', overflow: 'hidden' }} aria-hidden="true">
                                        <div style={{ width: `${maxArchetype > 0 ? Math.round((a.count / maxArchetype) * 100) : 0}%`, height: '100%', background: '#38bdf8', opacity: 0.7 }} />
                                    </div>
                                    <span style={{ flex: '0 0 1.4rem', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.76rem', fontWeight: 700, color: '#e2e8f0' }}>{a.count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Tertiary: narrative flavor — styled as league storyline cards, not
                a utility bullet list (Brief 4.5, criterion #5). */}
            {storylines.length > 0 && (
                <div className="dm-panel" style={{ padding: '0.85rem 1rem' }}>
                    <p className="dm-kicker" style={{ margin: '0 0 0.6rem' }}>Around the League</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {storylines.map((s, i) => (
                            <p
                                key={i}
                                style={{
                                    margin: 0,
                                    paddingLeft: '0.75rem',
                                    borderLeft: '2px solid #6366f1',
                                    color: '#cbd5e1',
                                    fontSize: '0.84rem',
                                    lineHeight: 1.5,
                                    fontStyle: 'italic',
                                }}
                            >
                                {s}
                            </p>
                        ))}
                    </div>
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

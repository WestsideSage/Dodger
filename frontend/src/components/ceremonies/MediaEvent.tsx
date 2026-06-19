import { useState } from 'react';
import type { OffseasonBeat, MediaEventOption } from '../../types';
import { ActionButton, PageHeader } from '../ui';

type MediaBeat = Extract<OffseasonBeat, { key: 'media_event' }>;

function effectChips(o: MediaEventOption) {
    const bits: string[] = [];
    if (o.fans) bits.push(`${o.fans > 0 ? '+' : ''}${o.fans} fans`);
    if (o.prestige) bits.push(`${o.prestige > 0 ? '+' : ''}${o.prestige} prestige`);
    if (o.credibility) bits.push(`${o.credibility > 0 ? '+' : ''}${o.credibility} credibility`);
    return bits.join(' · ') || 'no effect';
}

export function MediaEvent({
    beat,
    onChoose,
    onComplete,
    acting,
}: {
    beat: MediaBeat;
    onChoose: (optionKey: string) => void;
    onComplete: () => void;
    acting?: boolean;
}) {
    const { event, committed, result } = beat.payload;
    // PT5: latch the picked option visually so it's clear what will commit
    // before "Confirm & Continue" (the choice previously showed no selected state).
    const [chosenKey, setChosenKey] = useState<string | null>(null);
    const handleChoose = (key: string) => {
        setChosenKey(key);
        onChoose(key);
    };

    return (
        <section className="command-offseason-shell" data-testid="offseason-media">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · The Crowd`}
                title="Media Moment"
                description="How you play the press shapes your fans, reputation, and recruiting buzz — never the court."
            />

            {committed && result ? (
                <div className="dm-panel" data-testid="media-result" style={{ padding: '0.85rem 1rem' }}>
                    <p className="dm-kicker" style={{ margin: '0 0 0.4rem' }}>Played</p>
                    <p style={{ margin: 0, color: '#cbd5e1', fontSize: '0.88rem' }}>{result.receipt}</p>
                </div>
            ) : event ? (
                <div className="dm-panel" data-testid="media-event" style={{ padding: '0.85rem 1rem' }}>
                    <p style={{ margin: '0 0 0.7rem', color: '#e2e8f0', fontWeight: 600 }}>{event.prompt}</p>
                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                        {event.options.map((o) => {
                            const selected = o.key === chosenKey;
                            return (
                            <div
                                key={o.key}
                                aria-pressed={selected}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
                                    padding: '0.55rem 0.75rem', borderRadius: '6px',
                                    border: selected ? '1px solid #38bdf8' : '1px solid #1e293b',
                                    background: selected ? 'rgba(56,189,248,0.12)' : 'rgba(15,23,42,0.4)',
                                }}
                            >
                                <span style={{ color: '#e2e8f0' }}>{o.label}</span>
                                <span style={{ color: '#64748b', fontSize: '0.74rem' }}>{effectChips(o)}</span>
                                <span style={{ marginLeft: 'auto' }}>
                                    <ActionButton
                                        variant={selected ? 'secondary' : 'primary'}
                                        onClick={() => handleChoose(o.key)}
                                        disabled={acting}
                                    >
                                        {selected ? 'Selected ✓' : 'Choose'}
                                    </ActionButton>
                                </span>
                            </div>
                            );
                        })}
                    </div>
                </div>
            ) : (
                <div className="dm-panel" style={{ padding: '0.85rem 1rem', color: '#94a3b8' }}>
                    Quiet news cycle — nothing to weigh in on this offseason.
                </div>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>{committed ? 'Continue to the next beat.' : 'Pick a response, then continue.'}</p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton variant="primary" onClick={onComplete} disabled={acting}>
                        {acting ? 'Working…' : committed ? 'Continue' : 'Confirm & Continue'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
}

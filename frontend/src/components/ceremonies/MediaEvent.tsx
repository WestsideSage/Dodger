import { useState } from 'react';
import type { OffseasonBeat, MediaEventOption } from '../../types';
import { ActionButton, PageHeader } from '../../ui';
import styles from './MediaEvent.module.css';

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
                <div className={`dm-panel ${styles.resultPanel}`} data-testid="media-result">
                    <p className={`dm-kicker ${styles.resultKicker}`}>Played</p>
                    <p className={styles.resultBody}>{result.receipt}</p>
                </div>
            ) : event ? (
                <div className={`dm-panel ${styles.eventPanel}`} data-testid="media-event">
                    <p className={styles.prompt}>{event.prompt}</p>
                    <div className={styles.options}>
                        {event.options.map((o) => {
                            const selected = o.key === chosenKey;
                            return (
                            <div
                                key={o.key}
                                aria-pressed={selected}
                                className={`${styles.option} ${selected ? styles.optionSelected : ''}`}
                            >
                                <span className={styles.optionLabel}>{o.label}</span>
                                <span className={styles.optionChips}>{effectChips(o)}</span>
                                <span className={styles.optionAction}>
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
                <div className={`dm-panel ${styles.quiet}`}>
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

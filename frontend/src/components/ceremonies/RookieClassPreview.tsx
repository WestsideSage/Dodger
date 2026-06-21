import type { CSSProperties } from 'react';
import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader, Truncate } from '../../ui';
import styles from './RookieClassPreview.module.css';

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
    // Playtest 3: headline the class's UPSIDE (bands that top out at 70+) —
    // the old headline counted 70+ FLOORS, which is honestly ~0 in every
    // class and read as "elite talent doesn't exist in this league". The
    // floor count survives below as the "sure things" secondary stat.
    const ceilingProspects = beat.payload.ceiling_prospects ?? 0;

    const hasUpside = ceilingProspects > 0;
    const qualityPct = class_size > 0 ? Math.round((ceilingProspects / class_size) * 100) : 0;
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

            {/* Primary signal: class upside. ceiling_prospects is the single
                number that should drive how aggressively the player spends
                slots (Brief 4.5, criterion #1; playtest 3 metric fix). */}
            <div className={`dm-panel ${styles.upsidePanel} ${hasUpside ? styles.upsidePanelHas : ''}`}>
                <div className={styles.upsideFigure}>
                    <div className={`${styles.upsideNumber} ${hasUpside ? styles.upsideNumberHas : ''}`}>
                        {ceilingProspects}
                    </div>
                    <div className={styles.upsideCaption}>
                        70+ Upside
                    </div>
                </div>
                <div className={styles.upsideBody}>
                    <p className={styles.upsideHeadline}>
                        {hasUpside
                            ? `${ceilingProspects} of ${class_size} rookies scout a ceiling of 70+ OVR`
                            : 'No rookie scouts a 70+ ceiling this year — a thin class up top'}
                    </p>
                    {/* Explainer rendered as visible text on all devices — was a
                        hover-only title attribute (Brief 4.5, criterion #3). */}
                    <p className={styles.upsideExplain}>
                        A 70+ ceiling means the scouted range tops out that high — worth slots and
                        development time.
                        {top_prospects > 0
                            ? ` ${top_prospects} of them scout a 70+ FLOOR — already that good before development.`
                            : ' None carry a 70+ floor — every gem here still needs developing.'}
                    </p>
                    {class_size > 0 && (
                        <div className={styles.qualityWrap} aria-hidden="true">
                            <div className={styles.qualityTrack}>
                                <div
                                    className={`${styles.qualityFill} ${hasUpside ? styles.qualityFillHas : ''}`}
                                    style={{ '--bar-pct': `${qualityPct}%` } as CSSProperties}
                                />
                            </div>
                            <span className={styles.qualityLabel}>
                                {qualityPct}% of the class
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Secondary: class composition. class_size headlines; free_agents
                demoted to an inline footnote (Brief 4.5, criterion #2). */}
            <div className={`dm-panel ${styles.compPanel}`}>
                <dl className={styles.compList}>
                    <div>
                        <dd className={styles.compValue}>{class_size}</dd>
                        <dt className={styles.compLabel}>Incoming Rookies</dt>
                    </div>
                    <div className={styles.compFa}>
                        <dt className={styles.compLabel}>Veteran Free Agents</dt>
                        <dd className={styles.compFaValue}>{free_agents} also available</dd>
                    </div>
                </dl>

                {archetypes.length > 0 && (
                    <div className={styles.archetypes}>
                        <p className={`dm-kicker ${styles.archetypeKicker}`}>Archetype Breakdown</p>
                        <div className={styles.archetypeRows}>
                            {archetypes.map((a) => (
                                <div key={a.name} className={styles.archetypeRow}>
                                    <Truncate className={styles.archetypeName}>{a.name}</Truncate>
                                    <div className={styles.archetypeTrack} aria-hidden="true">
                                        <div
                                            className={styles.archetypeFill}
                                            style={{ '--bar-pct': `${maxArchetype > 0 ? Math.round((a.count / maxArchetype) * 100) : 0}%` } as CSSProperties}
                                        />
                                    </div>
                                    <span className={styles.archetypeCount}>{a.count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Tertiary: narrative flavor — styled as league storyline cards, not
                a utility bullet list (Brief 4.5, criterion #5). */}
            {storylines.length > 0 && (
                <div className={`dm-panel ${styles.storyPanel}`}>
                    <p className={`dm-kicker ${styles.archetypeKicker}`}>Around the League</p>
                    <div className={styles.storyList}>
                        {storylines.map((s, i) => (
                            <p key={i} className={styles.story}>
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

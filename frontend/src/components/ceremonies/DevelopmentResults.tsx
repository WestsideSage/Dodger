import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../../ui';
import { TermTip } from '../../legibility';
import styles from './DevelopmentResults.module.css';

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
    const trainingCredit = beat.payload.training_credit;

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

            <div className={`dm-panel ${styles.panel}`}>
                {players.length === 0 ? (
                    <p className={styles.empty}>
                        No development data available for your roster.
                    </p>
                ) : (
                    players.map((player, i) => {
                        const improved = player.delta > 0;
                        const declined = player.delta < 0;
                        const deltaClass = improved ? styles.deltaUp : declined ? styles.deltaDown : styles.deltaFlat;
                        const deltaLabel = player.delta > 0 ? `+${player.delta}` : `${player.delta}`;

                        const ovrDisplay = `${Math.round(player.ovr_before)} → ${Math.round(player.ovr_after)}`;

                        const movedAttrs = player.attr_deltas
                            ? Object.entries(player.attr_deltas).filter(([, v]) => v !== 0)
                            : [];

                        return (
                            <div key={i} className={styles.row}>
                                <div className={styles.rowHead}>
                                    <div className={styles.rowName}>
                                        <span className={styles.name}>
                                            {player.name}
                                        </span>
                                        {player.potential_ceiling != null && (
                                            <span className={styles.ceiling}>
                                                <TermTip term="growth.ceiling">Ceiling</TermTip>{' '}{player.potential_ceiling}
                                            </span>
                                        )}
                                        {player.notes && player.notes.length > 0 && (
                                            <div className={styles.notes}>
                                                {player.notes.map((note: string, idx: number) => (
                                                    <span key={idx} className={styles.note}>
                                                        ✨ {note}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <span className={styles.ovr}>
                                        {ovrDisplay}
                                    </span>
                                    <span className={`${styles.delta} ${deltaClass}`}>
                                        {deltaLabel}
                                    </span>
                                </div>
                                {movedAttrs.length > 0 && (
                                    <div className={styles.attrs}>
                                        {movedAttrs.map(([attr, val]) => {
                                            const attrClass = val > 0 ? styles.attrUp : styles.attrDown;
                                            const label = _ATTR_LABEL[attr] ?? attr;
                                            const termId =
                                                attr === 'throw_selection_iq' ? 'attr.throw_selection_iq' as const
                                                : attr === 'catch_courage' ? 'attr.catch_courage' as const
                                                : null;
                                            return (
                                                <span key={attr} className={styles.attr}>
                                                    {termId ? (
                                                        <TermTip term={termId}>{label}</TermTip>
                                                    ) : (
                                                        label
                                                    )}{' '}
                                                    <span className={attrClass}>
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

            {/* Playtest 3 F-7: the +0.2/week training credit is disclosed in
                Program Settings, so the beat that spends it must show the
                receipt — weeks run, credit banked, and the headroom caveat. */}
            {trainingCredit && trainingCredit.weeks > 0 && (
                <div className={styles.receipt} data-testid="training-credit-receipt">
                    <strong className={styles.receiptStrong}>
                        Training focus receipt:
                    </strong>{' '}
                    {trainingCredit.weeks} week{trainingCredit.weeks !== 1 ? 's' : ''} run
                    {trainingCredit.weeks > trainingCredit.week_cap
                        ? ` (${trainingCredit.credited_weeks} credited — cap ${trainingCredit.week_cap})`
                        : ''}{' '}
                    × +{trainingCredit.per_week_ovr} OVR = <strong className={styles.receiptValue}>
                    +{trainingCredit.credit_ovr.toFixed(1)} OVR</strong> of practice growth folded
                    into each player&apos;s development above (never past their ceiling).
                </div>
            )}

            <div className={styles.checklist}>
                <div className={styles.checklistIcon} aria-hidden="true">⏳</div>
                <div>
                  <h4 className={styles.checklistTitle}>
                    League Transition Checklist Completed
                  </h4>
                  <p className={styles.checklistBody}>
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

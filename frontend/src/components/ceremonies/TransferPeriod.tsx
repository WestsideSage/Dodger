import { useState } from 'react';
import type { OffseasonBeat, TransferExpiringRow, TransferBuyoutRow } from '../../types';
import { formatK } from '../../money';
import { ActionButton, PageHeader, Truncate } from '../../ui';
import styles from './TransferPeriod.module.css';

type TransferBeat = Extract<OffseasonBeat, { key: 'transfer_period' }>;

export function TransferPeriod({
    beat,
    onTransfer,
    onComplete,
    acting,
}: {
    beat: TransferBeat;
    onTransfer: (action: string, playerId: string, offerK?: number) => void;
    onComplete: () => void;
    acting?: boolean;
}) {
    const { expiring, buyouts, results, treasury_k, wage_bill_k } = beat.payload;
    // PT5: latch each decision optimistically so the row's selected state updates
    // the instant you click (the default 'resign'/'refuse' already styled one
    // button, so clicking the default showed no change — the choice "didn't
    // latch"). Keyed by player_id -> the onTransfer action string.
    const [pending, setPending] = useState<Record<string, string>>({});
    const handleTransfer = (action: string, playerId: string, offerK?: number) => {
        setPending((prev) => ({ ...prev, [playerId]: action }));
        onTransfer(action, playerId, offerK);
    };

    return (
        <section className="command-offseason-shell" data-testid="offseason-transfer">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · The Market`}
                title="Transfer Period"
                description="Re-sign your expiring players, weigh incoming buyouts, and hold off the clubs above you. Confirm to commit."
                stats={
                    <div className={styles.treasury}>
                        <span>Treasury <strong className={treasury_k < 0 ? styles.treasuryBad : styles.treasuryOk}>{formatK(treasury_k)}</strong></span>
                        <span>Wage bill <strong className={styles.treasuryBad}>{formatK(wage_bill_k)}</strong></span>
                    </div>
                }
            />

            {results ? (
                <ResultsView results={results} />
            ) : (
                <>
                    {expiring.length > 0 && (
                        <div className={`dm-panel ${styles.panel}`} data-testid="transfer-expiring">
                            <p className={`dm-kicker ${styles.kicker}`}>Expiring Contracts ({expiring.length})</p>
                            <div className={styles.rows}>
                                {expiring.map((row) => (
                                    <ExpiringRow
                                        key={row.player_id}
                                        row={row}
                                        onTransfer={handleTransfer}
                                        pendingAction={pending[row.player_id]}
                                        acting={acting}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {buyouts.length > 0 && (
                        <div className={`dm-panel ${styles.panel}`} data-testid="transfer-buyouts">
                            <p className={`dm-kicker ${styles.kicker}`}>Incoming Buyout Offers ({buyouts.length})</p>
                            <div className={styles.rows}>
                                {buyouts.map((row) => (
                                    <BuyoutRow
                                        key={row.player_id}
                                        row={row}
                                        onTransfer={handleTransfer}
                                        pendingAction={pending[row.player_id]}
                                        acting={acting}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {expiring.length === 0 && buyouts.length === 0 && (
                        <div className={`dm-panel ${styles.empty}`}>
                            No contracts to resolve this offseason — your squad is locked in.
                        </div>
                    )}
                </>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>{results ? 'Continue to the next beat.' : 'Confirm your decisions and continue.'}</p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton variant="primary" onClick={onComplete} disabled={acting}>
                        {acting ? 'Working…' : results ? 'Continue' : 'Confirm & Continue'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
}

function ExpiringRow({
    row,
    onTransfer,
    pendingAction,
    acting,
}: {
    row: TransferExpiringRow;
    onTransfer: (action: string, playerId: string, offerK?: number) => void;
    pendingAction?: string;
    acting?: boolean;
}) {
    // The just-clicked decision wins (optimistic); else the committed one.
    const decision = pendingAction === 'release' ? 'release'
        : pendingAction === 'resign' ? 'resign'
        : row.decision;
    const releasing = decision === 'release';
    // PT6: a dealbreaker veto means he WON'T re-sign (the Re-sign button is
    // disabled) — the latch badge must say so, not "Re-signing", or it
    // contradicts the "won't re-sign" warning on the same row.
    const badge = row.veto
        ? { text: "✗ Won't re-sign", className: styles.latchResign }
        : releasing
        ? { text: '✗ Letting walk', className: styles.latchWalk }
        : { text: '✓ Re-signing', className: styles.latchSelling };
    return (
        <div
            data-testid={`transfer-expiring-${row.player_id}`}
            className={`${styles.row} ${releasing ? styles.rowReleasing : ''}`}
        >
            <Truncate className={styles.name}>{row.name}</Truncate>
            <span className={styles.meta}>OVR {row.ovr}</span>
            <span className={styles.metaAlt}>asks {formatK(row.ask_k)}</span>
            {/* PT5/PT6: an explicit, unambiguous latch of the current decision
                (veto-aware — a "won't re-sign" player never reads as "Re-signing"). */}
            <span className={`${styles.latch} ${badge.className}`}>
                {badge.text}
            </span>
            {row.veto && (
                <span title={`Dealbreaker: ${row.dealbreaker} (${row.dealbreaker_letter})`} className={styles.veto}>
                    ⚠ {row.dealbreaker} {row.dealbreaker_letter} — won't re-sign
                </span>
            )}
            {row.top_suitor && (
                <Truncate className={styles.suitor}>
                    chased by {row.top_suitor.club_name} ({formatK(row.top_suitor.offer_k)})
                </Truncate>
            )}
            <span className={styles.actions}>
                <ActionButton
                    variant={!releasing ? 'primary' : 'ghost'}
                    onClick={() => onTransfer('resign', row.player_id, row.ask_k)}
                    disabled={acting || row.veto}
                >
                    Re-sign
                </ActionButton>
                <ActionButton
                    variant={releasing ? 'danger' : 'ghost'}
                    onClick={() => onTransfer('release', row.player_id)}
                    disabled={acting}
                >
                    Let walk
                </ActionButton>
            </span>
        </div>
    );
}

function BuyoutRow({
    row,
    onTransfer,
    pendingAction,
    acting,
}: {
    row: TransferBuyoutRow;
    onTransfer: (action: string, playerId: string, offerK?: number) => void;
    pendingAction?: string;
    acting?: boolean;
}) {
    const decision = pendingAction === 'accept_buyout' ? 'accept'
        : pendingAction === 'refuse_buyout' ? 'refuse'
        : row.decision;
    const accepting = decision === 'accept';
    return (
        <div
            data-testid={`transfer-buyout-${row.player_id}`}
            className={`${styles.row} ${accepting ? styles.rowAccepting : ''}`}
        >
            <Truncate className={styles.name}>{row.name}</Truncate>
            <span className={styles.metaAlt}>
                {row.buyer_club_name} (Tier {row.buyer_tier}) bids <strong className={styles.income}>{formatK(row.fee_k)}</strong>
            </span>
            {/* PT5: explicit latch of the current decision. */}
            <span className={`${styles.latch} ${accepting ? styles.latchSelling : styles.latchKeeping}`}>
                {accepting ? '✓ Selling' : '✓ Keeping him'}
            </span>
            <span className={styles.actions}>
                <ActionButton
                    variant={accepting ? 'primary' : 'ghost'}
                    onClick={() => onTransfer('accept_buyout', row.player_id)}
                    disabled={acting}
                >
                    Accept {formatK(row.fee_k)}
                </ActionButton>
                <ActionButton
                    variant={!accepting ? 'primary' : 'ghost'}
                    onClick={() => onTransfer('refuse_buyout', row.player_id)}
                    disabled={acting}
                >
                    Keep him
                </ActionButton>
            </span>
        </div>
    );
}

function ResultsView({
    results,
}: {
    results: NonNullable<TransferBeat['payload']['results']>;
}) {
    return (
        <div className={`dm-panel ${styles.panel}`} data-testid="transfer-results">
            <p className={`dm-kicker ${styles.kicker}`}>Transfer Period Settled</p>
            {results.resigned.length > 0 && (
                <p className={styles.resultLine}>
                    Re-signed{' '}
                    {results.resigned.map((r, i) => (
                        <span key={i}>{i > 0 ? ', ' : ''}<strong className={styles.income}>{r.name}</strong> ({formatK(r.salary_k)})</span>
                    ))}.
                </p>
            )}
            {results.sold.length > 0 && (
                <p className={styles.resultLine}>
                    Sold{' '}
                    {results.sold.map((s, i) => (
                        <span key={i}>{i > 0 ? ', ' : ''}<strong className={styles.resultName}>{s.name}</strong> to {s.buyer} for <strong className={styles.income}>{formatK(s.fee_k)}</strong></span>
                    ))}.
                </p>
            )}
            {results.departed.length > 0 && (
                <div className={styles.departedList}>
                    {results.departed.map((d, i) => (
                        <p key={i} className={styles.departed}>
                            ↘ <strong>{d.name}</strong> — {d.receipt}
                        </p>
                    ))}
                </div>
            )}
            {results.resigned.length === 0 && results.sold.length === 0 && results.departed.length === 0 && (
                <p className={styles.noMoves}>No moves — your squad rolls on intact.</p>
            )}
        </div>
    );
}

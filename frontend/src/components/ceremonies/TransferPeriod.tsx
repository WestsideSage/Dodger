import { useState } from 'react';
import type { OffseasonBeat, TransferExpiringRow, TransferBuyoutRow } from '../../types';
import { formatK } from '../../money';
import { ActionButton, PageHeader } from '../ui';

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
                    <div style={{ display: 'flex', gap: '1.1rem', fontSize: '0.8rem', color: '#cbd5e1' }}>
                        <span>Treasury <strong style={{ color: treasury_k < 0 ? '#f87171' : '#e2e8f0' }}>{formatK(treasury_k)}</strong></span>
                        <span>Wage bill <strong style={{ color: '#f87171' }}>{formatK(wage_bill_k)}</strong></span>
                    </div>
                }
            />

            {results ? (
                <ResultsView results={results} />
            ) : (
                <>
                    {expiring.length > 0 && (
                        <div className="dm-panel" data-testid="transfer-expiring" style={{ padding: '0.85rem 1rem' }}>
                            <p className="dm-kicker" style={{ margin: '0 0 0.6rem' }}>Expiring Contracts ({expiring.length})</p>
                            <div style={{ display: 'grid', gap: '0.5rem' }}>
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
                        <div className="dm-panel" data-testid="transfer-buyouts" style={{ padding: '0.85rem 1rem' }}>
                            <p className="dm-kicker" style={{ margin: '0 0 0.6rem' }}>Incoming Buyout Offers ({buyouts.length})</p>
                            <div style={{ display: 'grid', gap: '0.5rem' }}>
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
                        <div className="dm-panel" style={{ padding: '0.85rem 1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
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
    return (
        <div
            data-testid={`transfer-expiring-${row.player_id}`}
            style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
                padding: '0.55rem 0.75rem', borderRadius: '6px',
                border: `1px solid ${releasing ? '#7f1d1d' : '#1e293b'}`,
                background: releasing ? 'rgba(239,68,68,0.05)' : 'rgba(15,23,42,0.4)',
            }}
        >
            <span style={{ fontWeight: 700, color: '#e2e8f0' }}>{row.name}</span>
            <span style={{ color: '#64748b', fontSize: '0.78rem' }}>OVR {row.ovr}</span>
            <span style={{ color: '#94a3b8', fontSize: '0.78rem' }}>asks {formatK(row.ask_k)}</span>
            {/* PT5: an explicit, unambiguous latch of the current decision. */}
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: releasing ? '#f87171' : '#38bdf8' }}>
                {releasing ? '✗ Letting walk' : '✓ Re-signing'}
            </span>
            {row.veto && (
                <span title={`Dealbreaker: ${row.dealbreaker} (${row.dealbreaker_letter})`} style={{ color: '#f87171', fontSize: '0.72rem', fontWeight: 600 }}>
                    ⚠ {row.dealbreaker} {row.dealbreaker_letter} — won't re-sign
                </span>
            )}
            {row.top_suitor && (
                <span style={{ color: '#fb923c', fontSize: '0.74rem' }}>
                    chased by {row.top_suitor.club_name} ({formatK(row.top_suitor.offer_k)})
                </span>
            )}
            <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem' }}>
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
            style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
                padding: '0.55rem 0.75rem', borderRadius: '6px',
                border: `1px solid ${accepting ? '#065f46' : '#1e293b'}`,
                background: accepting ? 'rgba(16,185,129,0.06)' : 'rgba(15,23,42,0.4)',
            }}
        >
            <span style={{ fontWeight: 700, color: '#e2e8f0' }}>{row.name}</span>
            <span style={{ color: '#94a3b8', fontSize: '0.78rem' }}>
                {row.buyer_club_name} (Tier {row.buyer_tier}) bids <strong style={{ color: '#10b981' }}>{formatK(row.fee_k)}</strong>
            </span>
            {/* PT5: explicit latch of the current decision. */}
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: accepting ? '#10b981' : '#38bdf8' }}>
                {accepting ? '✓ Selling' : '✓ Keeping him'}
            </span>
            <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem' }}>
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
        <div className="dm-panel" data-testid="transfer-results" style={{ padding: '0.85rem 1rem' }}>
            <p className="dm-kicker" style={{ margin: '0 0 0.6rem' }}>Transfer Period Settled</p>
            {results.resigned.length > 0 && (
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                    Re-signed{' '}
                    {results.resigned.map((r, i) => (
                        <span key={i}>{i > 0 ? ', ' : ''}<strong style={{ color: '#10b981' }}>{r.name}</strong> ({formatK(r.salary_k)})</span>
                    ))}.
                </p>
            )}
            {results.sold.length > 0 && (
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                    Sold{' '}
                    {results.sold.map((s, i) => (
                        <span key={i}>{i > 0 ? ', ' : ''}<strong style={{ color: '#e2e8f0' }}>{s.name}</strong> to {s.buyer} for <strong style={{ color: '#10b981' }}>{formatK(s.fee_k)}</strong></span>
                    ))}.
                </p>
            )}
            {results.departed.length > 0 && (
                <div style={{ display: 'grid', gap: '0.35rem' }}>
                    {results.departed.map((d, i) => (
                        <p key={i} style={{ margin: 0, fontSize: '0.82rem', color: '#f87171' }}>
                            ↘ <strong>{d.name}</strong> — {d.receipt}
                        </p>
                    ))}
                </div>
            )}
            {results.resigned.length === 0 && results.sold.length === 0 && results.departed.length === 0 && (
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>No moves — your squad rolls on intact.</p>
            )}
        </div>
    );
}

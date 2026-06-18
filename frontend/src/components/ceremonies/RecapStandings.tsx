import type { OffseasonBeat } from '../../types';
import { formatK, formatKSigned } from '../../money';
import { ActionButton, PageHeader } from '../ui';

type RecapBeat = Extract<OffseasonBeat, { key: 'recap' }>;

function ordinal(n: number): string {
    const rem100 = n % 100;
    if (rem100 >= 11 && rem100 <= 13) return `${n}th`;
    switch (n % 10) {
        case 1: return `${n}st`;
        case 2: return `${n}nd`;
        case 3: return `${n}rd`;
        default: return `${n}th`;
    }
}

export function RecapStandings({
    beat,
    onComplete,
    acting,
}: {
    beat: RecapBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const standings = beat.payload.standings;
    // Work item #3: a truthful post-hoc statement that the season ended without
    // a playoff berth. Present ONLY when the backend confirmed the user's club
    // finished outside the cut (derived from the real playoff seeding), so it
    // never shows for a club that qualified.
    const missed = beat.payload.missed_playoffs;
    // V22 Phase 2: the season's settled books (league payout + playoff bonus
    // in, staff payroll out). Absent on pre-economy saves.
    const finances = beat.payload.finances;
    // V23: the season's league movement — promotions, relegations, WORLDS —
    // present on pyramid saves once the world's postseason is complete.
    const pyramid = beat.payload.pyramid;
    const userMovement = pyramid?.user?.movement;

    return (
        <section className="command-offseason-shell" data-testid="offseason-recap">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · Regular Season`}
                title="Final Regular-Season Table"
                description="Top four seeds qualify for the playoffs."
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

            {missed && (
                <div
                    data-testid="recap-missed-playoffs"
                    role="status"
                    style={{
                        margin: '0 1rem 1rem',
                        padding: '0.85rem 1rem',
                        background: 'linear-gradient(90deg, rgba(239,68,68,0.10), rgba(10,18,32,0) 70%)',
                        border: '1px solid #7f1d1d',
                        borderLeft: '3px solid #ef4444',
                        borderRadius: '6px',
                    }}
                >
                    <p
                        className="dm-kicker"
                        style={{ margin: 0, color: '#f87171', fontSize: '0.62rem' }}
                    >
                        Missed The Playoffs
                    </p>
                    <p style={{ margin: '0.3rem 0 0', color: '#e2e8f0', fontSize: '0.9rem', fontWeight: 600 }}>
                        You finished {ordinal(missed.finish)} of {missed.total} — the top {missed.cutoff} make the playoffs.
                    </p>
                    <p style={{ margin: '0.2rem 0 0', color: '#94a3b8', fontSize: '0.78rem' }}>
                        Season over; on to the offseason.
                    </p>
                </div>
            )}

            <div className="dm-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                        gap: '0 0.75rem',
                        padding: '0.5rem 1rem',
                        borderBottom: '1px solid #1e293b',
                        fontSize: '0.65rem',
                        color: '#475569',
                        letterSpacing: '0.06em',
                    }}
                >
                    <span>#</span>
                    <span>Club</span>
                    <span style={{ textAlign: 'center' }}>W-L-D</span>
                    <span style={{ textAlign: 'right' }}>Pts</span>
                    <span style={{ textAlign: 'right' }} title={beat.payload.diff_kind === 'game_points' ? 'Game-point differential: game points scored minus conceded' : 'Elimination differential: players eliminated minus players lost'}>{beat.payload.diff_kind === 'game_points' ? 'GP ±' : 'Elim ±'}</span>
                </div>

                {standings.map((row) => (
                    <div
                        key={row.rank}
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                            gap: '0 0.75rem',
                            padding: '0.6rem 1rem',
                            borderLeft: row.is_player_club ? '3px solid #f97316' : '3px solid transparent',
                            borderBottom: '1px solid #0f172a',
                            background: row.is_player_club ? '#1c1009' : 'transparent',
                            color: row.is_player_club ? '#fb923c' : '#94a3b8',
                            fontSize: '0.85rem',
                            alignItems: 'center',
                        }}
                    >
                        <span style={{ color: '#475569', fontSize: '0.75rem' }}>{row.rank}</span>
                        <span style={{ fontWeight: row.is_player_club ? 700 : 400, color: row.is_player_club ? '#fb923c' : '#e2e8f0' }}>
                            {row.club_name}
                        </span>
                        <span style={{ textAlign: 'center', color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                            {row.wins}-{row.losses}-{row.draws}
                        </span>
                        <span style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#e2e8f0' }}>
                            {row.points}
                        </span>
                        <span
                            style={{
                                textAlign: 'right',
                                fontVariantNumeric: 'tabular-nums',
                                color: row.diff > 0 ? '#10b981' : row.diff < 0 ? '#ef4444' : '#64748b',
                            }}
                        >
                            {row.diff > 0 ? '+' : ''}{row.diff}
                        </span>
                    </div>
                ))}
            </div>

            {finances && (
                <div
                    className="dm-panel"
                    data-testid="recap-finances"
                    style={{ padding: '0.85rem 1rem' }}
                >
                    <p className="dm-kicker" style={{ margin: '0 0 0.5rem' }}>Season Finances</p>
                    <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <span>
                            League payout <strong style={{ color: '#10b981' }}>{formatKSigned(finances.league_payout_k)}</strong>
                        </span>
                        {finances.playoff_bonus_k > 0 && (
                            <span>
                                Playoff bonus <strong style={{ color: '#10b981' }}>{formatKSigned(finances.playoff_bonus_k)}</strong>
                            </span>
                        )}
                        {finances.matchday_income_k != null && finances.matchday_income_k > 0 && (
                            <span>
                                Matchday <strong style={{ color: '#10b981' }}>{formatKSigned(finances.matchday_income_k)}</strong>
                            </span>
                        )}
                        {finances.merch_income_k != null && finances.merch_income_k > 0 && (
                            <span>
                                Merch <strong style={{ color: '#10b981' }}>{formatKSigned(finances.merch_income_k)}</strong>
                            </span>
                        )}
                        <span>
                            Staff payroll <strong style={{ color: '#f87171' }}>{formatKSigned(-finances.staff_payroll_k)}</strong>
                        </span>
                        {finances.player_wage_bill_k != null && finances.player_wage_bill_k > 0 && (
                            <span>
                                Player wages <strong style={{ color: '#f87171' }}>{formatKSigned(-finances.player_wage_bill_k)}</strong>
                            </span>
                        )}
                        <span>
                            Net <strong style={{ color: finances.net_k >= 0 ? '#10b981' : '#f87171' }}>{formatKSigned(finances.net_k)}</strong>
                        </span>
                        <span style={{ marginLeft: 'auto' }}>
                            Treasury <strong style={{ color: finances.closing_treasury_k < 0 ? '#f87171' : '#e2e8f0' }}>{formatK(finances.closing_treasury_k)}</strong>
                        </span>
                    </div>
                    {finances.closing_treasury_k < 0 && (
                        <p style={{ margin: '0.4rem 0 0', fontSize: '0.74rem', color: '#fb923c' }}>
                            Treasury is in the red — staff hiring is frozen until the books recover.
                        </p>
                    )}
                    <p style={{ margin: '0.4rem 0 0', fontSize: '0.7rem', color: '#64748b' }}>
                        {finances.rules}
                    </p>
                </div>
            )}

            {pyramid && (
                <div
                    className="dm-panel"
                    data-testid="recap-pyramid"
                    style={{ padding: '0.85rem 1rem' }}
                >
                    <p className="dm-kicker" style={{ margin: '0 0 0.5rem' }}>League Movement</p>
                    {userMovement && userMovement !== 'stays' && (
                        <p
                            style={{
                                margin: '0 0 0.6rem',
                                padding: '0.5rem 0.75rem',
                                borderRadius: '6px',
                                fontWeight: 700,
                                fontSize: '0.9rem',
                                color: userMovement === 'promoted' ? '#10b981' : '#f87171',
                                background: userMovement === 'promoted' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                                border: `1px solid ${userMovement === 'promoted' ? '#065f46' : '#7f1d1d'}`,
                            }}
                        >
                            {userMovement === 'promoted'
                                ? `PROMOTED — next season you play in the ${pyramid.user.division_name}.`
                                : `RELEGATED — next season you play in the ${pyramid.user.division_name}.`}
                        </p>
                    )}
                    <div style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem', color: '#cbd5e1' }}>
                        {pyramid.champions.map((champion) => (
                            <span key={champion.division_id}>
                                <strong style={{ color: '#e2e8f0' }}>{champion.division_name}:</strong>{' '}
                                {champion.club_name} are champions.
                            </span>
                        ))}
                        {pyramid.promoted.map((move) => (
                            <span key={`up-${move.from_division}`} style={{ color: '#10b981' }}>
                                ↑ {move.clubs.join(' and ')} go up to the {move.to_division}.
                            </span>
                        ))}
                        {pyramid.relegated.map((move) => (
                            <span key={`down-${move.from_division}`} style={{ color: '#f87171' }}>
                                ↓ {move.clubs.join(' and ')} drop to the {move.to_division}.
                            </span>
                        ))}
                        {pyramid.worlds && (
                            <span style={{ marginTop: '0.3rem', color: '#fbbf24' }}>
                                ★ WORLDS: {pyramid.worlds.champion_name} are World Champions
                                {pyramid.worlds.runner_up_name ? ` — ${pyramid.worlds.runner_up_name} fall in the final.` : '.'}
                            </span>
                        )}
                    </div>
                </div>
            )}

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

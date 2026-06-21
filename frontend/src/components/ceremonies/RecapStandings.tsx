import type { OffseasonBeat } from '../../types';
import { formatK, formatKSigned } from '../../money';
import { ActionButton, PageHeader, Truncate } from '../../ui';
import styles from './RecapStandings.module.css';
import chrome from '../chrome.module.css';

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
        <section className={chrome.offseasonShell} data-testid="offseason-recap">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · Regular Season`}
                title="Final Regular-Season Table"
                description="Top four seeds qualify for the playoffs."
                stats={
                    <div className={chrome.offseasonProgress} aria-label="Offseason beat progress">
                        {Array.from({ length: beat.total_beats }).map((_, index) => (
                            <span
                                key={index}
                                className={
                                    index <= beat.beat_index
                                        ? `${chrome.offseasonProgressStep} ${chrome.offseasonProgressStepActive}`
                                        : chrome.offseasonProgressStep
                                }
                            />
                        ))}
                    </div>
                }
            />

            {missed && (
                <div className={styles.missed} data-testid="recap-missed-playoffs" role="status">
                    <p className={`${chrome.dmKicker} ${styles.missedKicker}`}>
                        Missed The Playoffs
                    </p>
                    <p className={styles.missedFinish}>
                        You finished {ordinal(missed.finish)} of {missed.total} — the top {missed.cutoff} make the playoffs.
                    </p>
                    <p className={styles.missedNote}>
                        Season over; on to the offseason.
                    </p>
                </div>
            )}

            <div className={`${chrome.dmPanel} ${styles.tablePanel}`}>
                <div className={styles.tableHead}>
                    <span>#</span>
                    <span>Club</span>
                    <span className={styles.colCenter}>W-L-D</span>
                    <span className={styles.colRight}>Pts</span>
                    <span className={styles.colRight} title={beat.payload.diff_kind === 'game_points' ? 'Game-point differential: game points scored minus conceded' : 'Elimination differential: players eliminated minus players lost'}>{beat.payload.diff_kind === 'game_points' ? 'GP ±' : 'Elim ±'}</span>
                </div>

                {standings.map((row) => (
                    <div
                        key={row.rank}
                        className={`${styles.tableRow} ${row.is_player_club ? styles.tableRowPlayer : ''}`}
                    >
                        <span className={styles.rank}>{row.rank}</span>
                        <span className={row.is_player_club ? styles.clubPlayer : styles.club}>
                            <Truncate>{row.club_name}</Truncate>
                        </span>
                        <span className={styles.wld}>
                            {row.wins}-{row.losses}-{row.draws}
                        </span>
                        <span className={styles.pts}>
                            {row.points}
                        </span>
                        <span
                            className={`${styles.diff} ${row.diff > 0 ? styles.diffUp : row.diff < 0 ? styles.diffDown : styles.diffFlat}`}
                        >
                            {row.diff > 0 ? '+' : ''}{row.diff}
                        </span>
                    </div>
                ))}
            </div>

            {finances && (
                <div className={`${chrome.dmPanel} ${styles.financesPanel}`} data-testid="recap-finances">
                    <p className={`${chrome.dmKicker} ${styles.kicker}`}>Season Finances</p>
                    <div className={styles.financesRow}>
                        <span>
                            League payout <strong className={styles.income}>{formatKSigned(finances.league_payout_k)}</strong>
                        </span>
                        {finances.playoff_bonus_k > 0 && (
                            <span>
                                Playoff bonus <strong className={styles.income}>{formatKSigned(finances.playoff_bonus_k)}</strong>
                            </span>
                        )}
                        {finances.matchday_income_k != null && finances.matchday_income_k > 0 && (
                            <span>
                                Matchday <strong className={styles.income}>{formatKSigned(finances.matchday_income_k)}</strong>
                            </span>
                        )}
                        {finances.merch_income_k != null && finances.merch_income_k > 0 && (
                            <span>
                                Merch <strong className={styles.income}>{formatKSigned(finances.merch_income_k)}</strong>
                            </span>
                        )}
                        <span>
                            Staff payroll <strong className={styles.expense}>{formatKSigned(-finances.staff_payroll_k)}</strong>
                        </span>
                        {finances.player_wage_bill_k != null && finances.player_wage_bill_k > 0 && (
                            <span>
                                Player wages <strong className={styles.expense}>{formatKSigned(-finances.player_wage_bill_k)}</strong>
                            </span>
                        )}
                        <span>
                            Net <strong className={finances.net_k >= 0 ? styles.income : styles.expense}>{formatKSigned(finances.net_k)}</strong>
                        </span>
                        <span className={styles.treasury}>
                            Treasury <strong className={finances.closing_treasury_k < 0 ? styles.expense : styles.neutral}>{formatK(finances.closing_treasury_k)}</strong>
                        </span>
                    </div>
                    {finances.closing_treasury_k < 0 && (
                        <p className={styles.warnNote}>
                            Treasury is in the red — staff hiring is frozen until the books recover.
                        </p>
                    )}
                    <p className={styles.rulesNote}>
                        {finances.rules}
                    </p>
                </div>
            )}

            {pyramid && (
                <div className={`${chrome.dmPanel} ${styles.pyramidPanel}`} data-testid="recap-pyramid">
                    <p className={`${chrome.dmKicker} ${styles.kicker}`}>League Movement</p>
                    {userMovement && userMovement !== 'stays' && (
                        <p
                            className={`${styles.movementBanner} ${userMovement === 'promoted' ? styles.promoted : styles.relegated}`}
                        >
                            {userMovement === 'promoted'
                                ? `PROMOTED — next season you play in the ${pyramid.user.division_name}.`
                                : `RELEGATED — next season you play in the ${pyramid.user.division_name}.`}
                        </p>
                    )}
                    <div className={styles.movementList}>
                        {pyramid.champions.map((champion) => (
                            <span key={champion.division_id}>
                                <strong className={styles.movementLabel}>{champion.division_name}:</strong>{' '}
                                {champion.club_name} are champions.
                            </span>
                        ))}
                        {pyramid.promoted.map((move) => (
                            <span key={`up-${move.from_division}`} className={styles.up}>
                                ↑ {move.clubs.join(' and ')} go up to the {move.to_division}.
                            </span>
                        ))}
                        {pyramid.relegated.map((move) => (
                            <span key={`down-${move.from_division}`} className={styles.down}>
                                ↓ {move.clubs.join(' and ')} drop to the {move.to_division}.
                            </span>
                        ))}
                        {pyramid.worlds && (
                            <span className={styles.worlds}>
                                ★ WORLDS: {pyramid.worlds.champion_name} are World Champions
                                {pyramid.worlds.runner_up_name ? ` — ${pyramid.worlds.runner_up_name} fall in the final.` : '.'}
                            </span>
                        )}
                        {/* PT6: the global line above names only the final's two clubs.
                            Receipt the user's OWN Worlds run when they reached it but
                            exited in the semifinal (champion/runner-up are already named). */}
                        {pyramid.worlds_user && pyramid.worlds_user.result === 'semifinalist' && (
                            <span className={styles.worldsUser}>
                                ★ You reached Worlds as the {{
                                    premier_champion: 'Premier champion',
                                    premier_runner_up: 'Premier runner-up',
                                    circuit_champion: 'International Circuit champion',
                                    circuit_runner_up: 'International Circuit runner-up',
                                }[pyramid.worlds_user.qualified_as]} — out in the semifinal.
                            </span>
                        )}
                    </div>
                </div>
            )}

            <div className={`${chrome.dmPanel} ${chrome.actionBar}`}>
                <div>
                    <p className={chrome.dmKicker}>Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className={chrome.actionButtons}>
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

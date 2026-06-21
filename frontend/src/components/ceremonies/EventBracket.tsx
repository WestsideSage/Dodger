import type { EventBracketRow, EventResultRow } from '../../types';
import { Truncate } from '../../ui';
import styles from './EventBracket.module.css';
import chrome from '../chrome.module.css';
import cer from './ceremony.module.css';

// A dedicated bracket display for the V27 event-result shape. The
// `EventBracketRow` the backend records is simpler than `PlayoffBracketMatch`
// (no scoreline / decided_by / narrative_note — just who played and who won),
// so a dedicated component reads cleaner than forcing PlayoffBracket's schema.
// Visual language mirrors PlayoffBracket's MatchCard so the two brackets feel
// like one product surface.

function EventMatchCard({
    row,
    label,
    playerClubId,
}: {
    row: EventBracketRow;
    label: string;
    playerClubId?: string | null;
}) {
    const homeWon = row.winner_club_id === row.home_club_id;
    const awayWon = row.winner_club_id === row.away_club_id;
    const playerInMatch =
        !!playerClubId && (row.home_club_id === playerClubId || row.away_club_id === playerClubId);
    const playerAdvanced = playerInMatch && row.winner_club_id === playerClubId;
    const playerEliminated = playerInMatch && !playerAdvanced;
    const cardOutcomeClass = playerAdvanced
        ? styles.cardAdvanced
        : playerEliminated
            ? styles.cardEliminated
            : styles.cardNeutral;

    const teamRow = (clubId: string, name: string, isWinner: boolean) => (
        <div
            key={clubId}
            className={`${styles.team} ${isWinner ? styles.teamWinner : ''}`}
        >
            <Truncate className={styles.teamName}>{name || clubId}</Truncate>
            <span className={isWinner ? styles.teamMarkWinner : styles.teamMark}>{isWinner ? 'W' : '·'}</span>
        </div>
    );

    return (
        <div
            data-player-outcome={playerAdvanced ? 'advanced' : playerEliminated ? 'eliminated' : undefined}
            className={`${styles.card} ${cardOutcomeClass}`}
        >
            <p className={`${chrome.dmKicker} ${styles.cardLabel}`}>
                <span>{label}</span>
                {(playerAdvanced || playerEliminated) && (
                    <span className={`${styles.outcomeChip} ${playerAdvanced ? styles.outcomeChipWon : styles.outcomeChipOut}`}>
                        {playerAdvanced ? 'YOU WON' : 'YOU OUT'}
                    </span>
                )}
            </p>
            {teamRow(row.home_club_id, row.home_club_name, homeWon)}
            {teamRow(row.away_club_id, row.away_club_name, awayWon)}
        </div>
    );
}

/** Group a flat bracket-row list into ordered round columns. */
function groupByRound(rows: EventBracketRow[]): { round: string; rows: EventBracketRow[] }[] {
    const order: string[] = [];
    const buckets: Record<string, EventBracketRow[]> = {};
    for (const r of rows) {
        if (!(r.round in buckets)) {
            buckets[r.round] = [];
            order.push(r.round);
        }
        buckets[r.round].push(r);
    }
    return order.map(round => ({ round, rows: buckets[round] }));
}

const _ROUND_LABEL: Record<string, string> = {
    final: 'Final',
    semifinal: 'Semifinals',
    quarterfinal: 'Quarterfinals',
    round1: 'Round 1',
    r1: 'Round 1',
    r2: 'Round 2',
};

function roundLabel(round: string, index: number): string {
    return _ROUND_LABEL[round.toLowerCase()] ?? `Round ${index + 1}`;
}

export function EventBracket({
    event,
    playerClubId,
}: {
    event: EventResultRow;
    playerClubId?: string | null;
}) {
    const groups = groupByRound(event.bracket);
    if (groups.length === 0) {
        return (
            <p className={`${cer['playoff-bracket-empty']} ${styles.empty}`}>
                Bracket details unavailable.
            </p>
        );
    }
    return (
        <section className={`${chrome.dmPanel} ${cer['playoff-bracket-panel']}`} data-testid="event-bracket">
            <div className={chrome.dmPanelHeader}>
                <p className={chrome.dmKicker}>{event.event_name}</p>
                <h2 className={chrome.dmPanelTitle}>Bracket</h2>
            </div>
            <div className={cer['playoff-bracket-grid']}>
                {groups.map((group, gi) => (
                    <div className={cer['playoff-bracket-column']} key={group.round}>
                        <p className={`${chrome.dmKicker} ${cer['playoff-bracket-round-label']}`}>
                            {roundLabel(group.round, gi)}
                        </p>
                        {group.rows.map((row, ri) => (
                            <EventMatchCard
                                key={`${group.round}-${ri}`}
                                row={row}
                                label={roundLabel(group.round, gi)}
                                playerClubId={playerClubId}
                            />
                        ))}
                    </div>
                ))}
                <div className={cer['playoff-bracket-column']}>
                    <p className={`${chrome.dmKicker} ${cer['playoff-bracket-round-label']}`}>Champion</p>
                    <div
                        className={`${cer['playoff-champion-card']} ${
                            event.champion_club_id === playerClubId ? cer['is-user'] : ''
                        }`}
                    >
                        <span className={cer['playoff-champion-trophy']} aria-hidden="true">🏆</span>
                        <strong>{event.champion_club_name || event.champion_club_id}</strong>
                        <span>{event.event_name} Champion</span>
                    </div>
                </div>
            </div>
        </section>
    );
}

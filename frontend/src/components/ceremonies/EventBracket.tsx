import type { EventBracketRow, EventResultRow } from '../../types';

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
    const outcomeBorder = playerAdvanced ? '#22c55e' : playerEliminated ? '#f43f5e' : '#1e293b';

    const teamRow = (clubId: string, name: string, isWinner: boolean) => (
        <div
            key={clubId}
            style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: '0.5rem',
                padding: '0.4rem 0.6rem',
                background: isWinner ? 'rgba(34,211,238,0.14)' : 'transparent',
                color: isWinner ? '#fff' : '#94a3b8',
                fontWeight: isWinner ? 700 : 500,
                borderRadius: '3px',
            }}
        >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {name || clubId}
            </span>
            <span style={{ color: isWinner ? '#22d3ee' : '#475569' }}>{isWinner ? 'W' : '·'}</span>
        </div>
    );

    return (
        <div
            data-player-outcome={playerAdvanced ? 'advanced' : playerEliminated ? 'eliminated' : undefined}
            style={{
                border: `1px solid ${outcomeBorder}`,
                borderLeft: playerInMatch ? `3px solid ${outcomeBorder}` : `1px solid ${outcomeBorder}`,
                borderRadius: '6px',
                background: 'rgba(2,6,23,0.55)',
                padding: '0.3rem',
                minWidth: '13rem',
            }}
        >
            <p
                className="dm-kicker"
                style={{
                    margin: '0 0 0.15rem 0.35rem',
                    fontSize: '0.55rem',
                    color: '#475569',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    flexWrap: 'wrap',
                }}
            >
                <span>{label}</span>
                {(playerAdvanced || playerEliminated) && (
                    <span
                        style={{
                            padding: '0.05rem 0.35rem',
                            fontSize: '0.5rem',
                            fontWeight: 800,
                            letterSpacing: '0.06em',
                            color: '#0b1220',
                            background: playerAdvanced ? '#22c55e' : '#f43f5e',
                            borderRadius: '2px',
                        }}
                    >
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
            <p className="playoff-bracket-empty" style={{ color: '#64748b' }}>
                Bracket details unavailable.
            </p>
        );
    }
    return (
        <section className="dm-panel playoff-bracket-panel" data-testid="event-bracket">
            <div className="dm-panel-header">
                <p className="dm-kicker">{event.event_name}</p>
                <h2 className="dm-panel-title">Bracket</h2>
            </div>
            <div className="playoff-bracket-grid">
                {groups.map((group, gi) => (
                    <div className="playoff-bracket-column" key={group.round}>
                        <p className="dm-kicker playoff-bracket-round-label">
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
                <div className="playoff-bracket-column">
                    <p className="dm-kicker playoff-bracket-round-label">Champion</p>
                    <div
                        className={`playoff-champion-card ${
                            event.champion_club_id === playerClubId ? 'is-user' : ''
                        }`}
                    >
                        <span className="playoff-champion-trophy" aria-hidden="true">🏆</span>
                        <strong>{event.champion_club_name || event.champion_club_id}</strong>
                        <span>{event.event_name} Champion</span>
                    </div>
                </div>
            </div>
        </section>
    );
}

import type { OffseasonBeat, EventResultRow } from '../../types';
import { ActionButton, PageHeader } from '../ui';
import { EventBracket } from './EventBracket';

type EventsBeat = Extract<OffseasonBeat, { key: 'events' }>;

const _EVENT_LABEL: Record<string, string> = {
    domestic_cup: 'Domestic Cup',
    cloth_classic: 'Cloth Classic',
    no_sting_open: 'No-Sting Open',
    msi: 'Midseason International',
    founders: "Founders' Exhibition",
};

function eventLabel(event: EventResultRow): string {
    return _EVENT_LABEL[event.event_key] ?? event.event_name ?? event.event_key;
}

function EventCard({
    event,
    playerClubId,
}: {
    event: EventResultRow;
    playerClubId?: string | null;
}) {
    const label = eventLabel(event);
    const meta = event.meta ?? {};
    const giantKillings: Array<{ winner: string; victim: string; receipt: string }> =
        Array.isArray((meta as Record<string, unknown>).giant_killings)
            ? ((meta as Record<string, unknown>).giant_killings as Array<{ winner: string; victim: string; receipt: string }>)
            : [];
    const worldsSeeding = Boolean((meta as Record<string, unknown>).worlds_seeding);
    const purseText = event.purse_k > 0 ? ` · +${event.purse_k}k purse` : '';

    return (
        <div className="dm-panel" data-testid="event-result-card" style={{ padding: '0.9rem 1rem' }}>
            <p className="dm-kicker" style={{ margin: '0 0 0.3rem' }}>{label}</p>
            <p style={{ margin: '0 0 0.5rem', color: '#e2e8f0', fontWeight: 600, fontSize: '1.05rem' }}>
                🏆 {event.champion_club_name || event.champion_club_id}
                <span style={{ color: '#64748b', fontWeight: 400, fontSize: '0.78rem' }}>{purseText}</span>
            </p>
            {worldsSeeding && (
                <p style={{ margin: '0 0 0.4rem', color: '#22d3ee', fontSize: '0.78rem' }}>
                    Worlds seeding note earned.
                </p>
            )}
            {giantKillings.length > 0 && (
                <ul style={{ margin: '0 0 0.5rem', paddingLeft: '1.1rem', color: '#f59e0b', fontSize: '0.8rem' }}>
                    {giantKillings.map((gk, i) => (
                        <li key={i} data-testid="giant-killing">
                            <strong>{gk.winner}</strong> giant-killed <strong>{gk.victim}</strong>
                            {gk.receipt ? ` — ${gk.receipt}` : ''}
                        </li>
                    ))}
                </ul>
            )}
            <EventBracket event={event} playerClubId={playerClubId} />
        </div>
    );
}

export function EventsBeat({
    beat,
    onComplete,
    acting,
    playerClubId,
}: {
    beat: EventsBeat;
    onComplete: () => void;
    acting?: boolean;
    playerClubId?: string | null;
}) {
    const events = beat.payload.events ?? [];
    const hasCup = events.some(e => e.event_key === 'domestic_cup');

    return (
        <section className="command-offseason-shell" data-testid="offseason-events">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · The Calendar`}
                title="The Season's Events"
                description="A calendar of real competitions — the Domestic Cup, ruleset invitationals, the Midseason International, and the Founders' Exhibition — each a deterministic auto-simmed knockout with a trophy, purse, and a story."
            />

            {events.length > 0 ? (
                <div style={{ display: 'grid', gap: '1rem' }}>
                    {events.map(event => (
                        <EventCard key={event.event_key} event={event} playerClubId={playerClubId} />
                    ))}
                </div>
            ) : (
                <div className="dm-panel" style={{ padding: '0.85rem 1rem', color: '#94a3b8' }}>
                    No events resolved this season.
                </div>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>
                        {hasCup
                            ? 'The cup is decided. Continue to the next beat.'
                            : 'Continue to the next offseason beat.'}
                    </p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton variant="primary" onClick={onComplete} disabled={acting}>
                        {acting ? 'Working…' : 'Continue'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
}

import { useState } from 'react';
import type { DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, Badge, Card, CompactList, CompactListRow, PageHeader, StatChip, StatusMessage } from './ui';

function label(value: string) {
  return value.replace(/_/g, ' ');
}

function ItemText({ item }: { item: Record<string, string | number | null> }) {
  const text = item.text ?? item.summary ?? item.award_type ?? item.club_a_name ?? item.status ?? '-';
  return <span className="font-bold">{String(text)}</span>;
}

export function DynastyOffice() {
  const { data, error, loading, setData, setError } = useApiResource<DynastyOfficeResponse>('/api/dynasty-office');
  const [busyId, setBusyId] = useState<string | null>(null);

  const savePromise = (playerId: string, promiseType: string) => {
    setBusyId(playerId);
    fetch('/api/dynasty-office/promises', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId, promise_type: promiseType }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Promise could not be saved');
        return res.json();
      })
      .then((payload: DynastyOfficeResponse) => setData(payload))
      .catch(err => setError(err.message))
      .finally(() => setBusyId(null));
  };

  const hireStaff = (candidateId: string) => {
    setBusyId(candidateId);
    fetch('/api/dynasty-office/staff/hire', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_id: candidateId }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Staff move could not be completed');
        return res.json();
      })
      .then((payload: DynastyOfficeResponse) => setData(payload))
      .catch(err => setError(err.message))
      .finally(() => setBusyId(null));
  };

  if (error) return <StatusMessage title="Dynasty office unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading dynasty office">Opening program files.</StatusMessage>;
  if (!data) return <StatusMessage title="No dynasty data">No program data returned.</StatusMessage>;

  return (
    <div className="flex flex-col gap-5" data-testid="dynasty-office">
      <PageHeader
        eyebrow="Program office"
        title="Dynasty Office"
        description="Late-roadmap systems exposed as honest program loops: promises, league memory, and staff movement."
        stats={
          <>
            <StatChip label="Credibility" value={data.recruiting.credibility.grade} tone="warning" />
            <StatChip label="Week" value={data.week} tone="info" />
            <StatChip label="Club" value={data.player_club_name} />
          </>
        }
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-display uppercase tracking-widest text-lg">Recruiting Promises</h3>
              <p className="mt-1 text-sm text-[var(--color-muted)]">{data.recruiting.rules.honesty}</p>
            </div>
            <Badge tone="warning">V8</Badge>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {data.recruiting.prospects.slice(0, 6).map(prospect => (
              <section key={prospect.player_id} className="rounded-md border border-[var(--color-border)] bg-[var(--color-cream)] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-bold">{prospect.name}</h4>
                    <p className="text-xs text-[var(--color-muted)]">
                      {prospect.public_archetype} · OVR {prospect.public_ovr_band.join('-')} · {prospect.hometown}
                    </p>
                  </div>
                  <Badge tone="info">Fit {prospect.fit_score}</Badge>
                </div>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[var(--color-muted)]">
                  {prospect.interest_evidence.map(item => <li key={item}>{item}</li>)}
                </ul>
                <div className="mt-3 flex flex-wrap gap-2">
                  {prospect.active_promise ? (
                    <Badge tone="success">{label(prospect.active_promise.promise_type)}</Badge>
                  ) : prospect.promise_options.map(option => (
                    <ActionButton
                      key={option}
                      variant="secondary"
                      className="min-h-8 px-2 py-1 text-[10px]"
                      disabled={busyId === prospect.player_id}
                      onClick={() => savePromise(prospect.player_id, option)}
                    >
                      {label(option)}
                    </ActionButton>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-display uppercase tracking-widest text-lg">Program Credibility</h3>
              <p className="mt-1 text-sm text-[var(--color-muted)]">Score {data.recruiting.credibility.score} · Grade {data.recruiting.credibility.grade}</p>
            </div>
            <Badge tone="info">{data.recruiting.active_promises.length}/{data.recruiting.rules.max_active_promises}</Badge>
          </div>
          <ul className="mt-3 list-disc space-y-2 pl-4 text-sm text-[var(--color-muted)]">
            {data.recruiting.credibility.evidence.map(item => <li key={item}>{item}</li>)}
          </ul>
          <div className="mt-4 flex flex-col gap-2">
            {data.recruiting.active_promises.map(promise => {
              const resultTone = promise.result === 'fulfilled' ? 'success'
                : promise.result === 'broken' ? 'danger'
                : 'info';
              const resultLabel = promise.result === 'fulfilled' ? 'FULFILLED'
                : promise.result === 'broken' ? 'BROKEN'
                : 'OPEN';
              return (
                <StatusMessage key={promise.player_id} title={label(promise.promise_type)} tone={resultTone}>
                  <div className="flex items-center gap-2">
                    <Badge tone={resultTone}>{resultLabel}</Badge>
                    <span>{promise.evidence}</span>
                  </div>
                </StatusMessage>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="font-display uppercase tracking-widest text-lg">League Memory</h3>
            <Badge tone="warning">V9</Badge>
          </div>
          <CompactList className="shadow-none">
            {data.league_memory.records.items.slice(0, 4).map((item, index) => (
              <CompactListRow key={`record-${index}`}>
                <ItemText item={item} />
              </CompactListRow>
            ))}
          </CompactList>
          <div className="mt-3 grid grid-cols-1 gap-2">
            {data.league_memory.recent_matches.map(match => (
              <div key={match.match_id} className="rounded-md border border-[var(--color-line)] p-2 text-sm">
                <strong>Week {match.week}</strong> · {match.summary} · {match.winner_name}
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-4 xl:col-span-2">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="font-display uppercase tracking-widest text-lg">Staff Market</h3>
            <Badge tone="warning">V10</Badge>
          </div>
          <p className="mb-3 text-sm text-[var(--color-muted)]">{data.staff_market.rules.honesty}</p>
          {data.staff_market.recent_actions.length > 0 && (
            <div className="mb-3 rounded-md border border-[var(--color-line)] bg-[var(--color-cream)] p-3">
              <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Recent staff moves</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {data.staff_market.recent_actions.map(action => (
                  <Badge key={action.candidate_id} tone="success">{label(action.department)}: {action.name}</Badge>
                ))}
              </div>
            </div>
          )}
          {data.staff_market.current_staff.length > 0 && (
            <div className="mb-3 rounded-md border border-[var(--color-line)] bg-[var(--color-cream)] p-3">
              <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Current staff</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {data.staff_market.current_staff.map((head) => {
                  const modifier = head.department === 'development'
                    ? Math.max(0, ((head.rating_primary - 50) / 50) * 0.15)
                    : 0;
                  const modifierPct = (modifier * 100).toFixed(1);
                  return (
                    <div key={head.department} className="flex items-center gap-2">
                      <Badge tone="info">{label(head.department)}: {head.name} ({head.rating_primary})</Badge>
                      {head.department === 'development' && modifier > 0 && (
                        <Badge tone="success">+{modifierPct}% dev</Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {data.staff_market.candidates.slice(0, 6).map(candidate => (
              <section key={candidate.candidate_id} className="rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h4 className="font-bold">{candidate.name}</h4>
                    <p className="text-xs uppercase tracking-wider text-[var(--color-muted)]">{label(candidate.department)}</p>
                  </div>
                  <Badge tone="info">{candidate.rating_primary}/{candidate.rating_secondary}</Badge>
                </div>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[var(--color-muted)]">
                  {candidate.effect_lanes.map(item => <li key={item}>{item}</li>)}
                </ul>
                <ActionButton
                  className="mt-3 min-h-8 px-3 py-1"
                  variant="accent"
                  disabled={busyId === candidate.candidate_id}
                  onClick={() => hireStaff(candidate.candidate_id)}
                >
                  Hire
                </ActionButton>
              </section>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

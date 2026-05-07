import { useState } from 'react';
import type { DynastyOfficeResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, Badge, CompactList, CompactListRow, PageHeader, StatChip, StatusMessage } from './ui';

function label(value: string) {
  return value.replace(/_/g, ' ');
}

function ItemText({ item }: { item: Record<string, string | number | null> }) {
  const text = item.text ?? item.summary ?? item.award_type ?? item.club_a_name ?? item.status ?? '-';
  return <span style={{ fontWeight: 700 }}>{String(text)}</span>;
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="dynasty-office">
      <PageHeader
        eyebrow="Dynasty Office"
        title="Dynasty Office"
        description="The nerve center of the program: manage recruiting promises, monitor league history, and oversee staff hiring."
        stats={
          <>
            <StatChip label="Credibility" value={data.recruiting.credibility.grade} tone="warning" />
            <StatChip label="Week" value={data.week} tone="info" />
            <StatChip label="Club" value={data.player_club_name} />
          </>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }} className="xl:grid-cols-[1.1fr_0.9fr]">
        {/* Recruiting Promises */}
        <div className="dm-panel">
          <div className="dm-panel-header" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
            <div>
              <p className="dm-kicker">Recruiting</p>
              <h3 className="dm-panel-title">Recruiting Promises</h3>
              <p className="dm-panel-subtitle">{data.recruiting.rules.honesty}</p>
            </div>
            <Badge tone="warning">V8</Badge>
          </div>
          <div className="dm-section" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.75rem' }} >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
              {data.recruiting.prospects.slice(0, 6).map(prospect => (
                <section
                  key={prospect.player_id}
                  style={{
                    borderRadius: '4px',
                    border: '1px solid #1e293b',
                    background: '#0f172a',
                    padding: '0.75rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div>
                      <h4 style={{ fontWeight: 700, margin: 0, color: '#fff' }}>{prospect.name}</h4>
                      <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '0.125rem 0 0' }}>
                        {prospect.public_archetype} · OVR {prospect.public_ovr_band.join('-')} · {prospect.hometown}
                      </p>
                    </div>
                    <Badge tone="info">Fit {prospect.fit_score}</Badge>
                  </div>
                  <ul style={{ marginTop: '0.5rem', paddingLeft: '1rem', listStyleType: 'disc', fontSize: '0.75rem', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '0.125rem' }}>
                    {prospect.interest_evidence.map(item => <li key={item}>{item}</li>)}
                  </ul>
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {prospect.active_promise ? (
                      <Badge tone="success">{label(prospect.active_promise.promise_type)}</Badge>
                    ) : prospect.promise_options.map(option => (
                      <ActionButton
                        key={option}
                        variant="secondary"
                        style={{ minHeight: '2rem', padding: '0.25rem 0.5rem', fontSize: '10px' }}
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
          </div>
        </div>

        {/* Program Credibility */}
        <div className="dm-panel">
          <div className="dm-panel-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
            <div>
              <p className="dm-kicker">Program</p>
              <h3 className="dm-panel-title">Program Credibility</h3>
              <p className="dm-panel-subtitle">Score {data.recruiting.credibility.score} · Grade {data.recruiting.credibility.grade}</p>
            </div>
            <Badge tone="info">{data.recruiting.active_promises.length}/{data.recruiting.rules.max_active_promises}</Badge>
          </div>
          <div className="dm-section" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <ul style={{ paddingLeft: '1rem', listStyleType: 'disc', fontSize: '0.875rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.5rem', margin: 0 }}>
              {data.recruiting.credibility.evidence.map(item => <li key={item}>{item}</li>)}
            </ul>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.recruiting.active_promises.map(promise => {
                const resultTone = promise.result === 'fulfilled' ? 'success'
                  : promise.result === 'broken' ? 'danger'
                  : 'info';
                const resultLabel = promise.result === 'fulfilled' ? 'FULFILLED'
                  : promise.result === 'broken' ? 'BROKEN'
                  : 'OPEN';
                return (
                  <StatusMessage key={promise.player_id} title={label(promise.promise_type)} tone={resultTone}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Badge tone={resultTone}>{resultLabel}</Badge>
                      <span>{promise.evidence}</span>
                    </div>
                  </StatusMessage>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }} className="xl:grid-cols-3">
        {/* League Memory */}
        <div className="dm-panel">
          <div className="dm-panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
            <div>
              <p className="dm-kicker">League</p>
              <h3 className="dm-panel-title">League Memory</h3>
            </div>
            <Badge tone="warning">V9</Badge>
          </div>
          <div className="dm-section" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <CompactList>
              {data.league_memory.records.items.slice(0, 4).map((item, index) => (
                <CompactListRow key={`record-${index}`}>
                  <ItemText item={item} />
                </CompactListRow>
              ))}
            </CompactList>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.league_memory.recent_matches.map(match => (
                <div
                  key={match.match_id}
                  style={{
                    borderRadius: '4px',
                    border: '1px solid #1e293b',
                    padding: '0.5rem 0.75rem',
                    fontSize: '0.875rem',
                    color: '#cbd5e1',
                  }}
                >
                  <strong style={{ color: '#fff' }}>Week {match.week}</strong>
                  {' · '}{match.summary}{' · '}{match.winner_name}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Staff Market */}
        <div className="dm-panel xl:col-span-2">
          <div className="dm-panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
            <div>
              <p className="dm-kicker">Front Office</p>
              <h3 className="dm-panel-title">Staff Market</h3>
            </div>
            <Badge tone="warning">V10</Badge>
          </div>
          <div className="dm-section" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <p style={{ fontSize: '0.875rem', color: '#64748b', margin: 0 }}>{data.staff_market.rules.honesty}</p>

            {data.staff_market.recent_actions.length > 0 && (
              <div style={{ borderRadius: '4px', border: '1px solid #1e293b', background: '#0f172a', padding: '0.75rem' }}>
                <div style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '11px', color: '#64748b' }}>Recent staff moves</div>
                <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {data.staff_market.recent_actions.map(action => (
                    <Badge key={action.candidate_id} tone="success">{label(action.department)}: {action.name}</Badge>
                  ))}
                </div>
              </div>
            )}

            {data.staff_market.current_staff.length > 0 && (
              <div style={{ borderRadius: '4px', border: '1px solid #1e293b', background: '#0f172a', padding: '0.75rem' }}>
                <div style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '11px', color: '#64748b' }}>Current staff</div>
                <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {data.staff_market.current_staff.map((head) => {
                    const modifier = head.department === 'development'
                      ? Math.max(0, ((head.rating_primary - 50) / 50) * 0.15)
                      : 0;
                    const modifierPct = (modifier * 100).toFixed(1);
                    return (
                      <div key={head.department} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
              {data.staff_market.candidates.slice(0, 6).map(candidate => (
                <section
                  key={candidate.candidate_id}
                  style={{
                    borderRadius: '4px',
                    border: '1px solid #1e293b',
                    background: '#0f172a',
                    padding: '0.75rem',
                  }}
                >
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div>
                      <h4 style={{ fontWeight: 700, margin: 0, color: '#fff' }}>{candidate.name}</h4>
                      <p style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.075em', color: '#64748b', margin: '0.125rem 0 0' }}>{label(candidate.department)}</p>
                    </div>
                    <Badge tone="info">{candidate.rating_primary}/{candidate.rating_secondary}</Badge>
                  </div>
                  <ul style={{ marginTop: '0.5rem', paddingLeft: '1rem', listStyleType: 'disc', fontSize: '0.75rem', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '0.125rem' }}>
                    {candidate.effect_lanes.map(item => <li key={item}>{item}</li>)}
                  </ul>
                  <ActionButton
                    style={{ marginTop: '0.75rem', minHeight: '2rem', padding: '0.25rem 0.75rem' }}
                    variant="accent"
                    disabled={busyId === candidate.candidate_id}
                    onClick={() => hireStaff(candidate.candidate_id)}
                  >
                    Hire
                  </ActionButton>
                </section>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { ActionButton } from '../ui';

interface ProspectOption {
  player_id: string;
  name: string;
  hometown: string;
  public_archetype: string;
  public_ovr_band: [number, number];
}

export function StartingRecruitmentStep({
  onCommit,
  onBack,
  creating,
}: {
  onCommit: (ids: string[]) => void;
  onBack: () => void;
  creating: boolean;
}) {
  const [prospects, setProspects] = useState<ProspectOption[]>([]);
  const [rosterIds, setRosterIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/saves/starting-prospects')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load prospects');
        return r.json();
      })
      .then(d => setProspects(d.prospects ?? []))
      .catch(err => setLoadError(err.message));
  }, []);

  const toggleProspect = (id: string) => {
    const next = new Set(rosterIds);
    if (next.has(id)) next.delete(id);
    else if (next.size < 10) next.add(id);
    setRosterIds(next);
  };

  const needed = 6 - rosterIds.size;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Step 3 of 3</p>
        <h2 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0, fontSize: '1.25rem' }}>
          Recruit Roster
        </h2>
        <p style={{ margin: '0.375rem 0 0', fontSize: '0.8125rem', color: '#64748b' }}>
          Select at least 6 players (max 10). {rosterIds.size > 0 && `${rosterIds.size} selected.`}
        </p>
      </div>

      {loadError && (
        <div style={{ padding: '0.75rem', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: '4px', color: '#fb7185', fontSize: '0.875rem' }}>
          {loadError}
        </div>
      )}

      {prospects.length === 0 && !loadError && (
        <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Loading prospects…</p>
      )}

      <div style={{ maxHeight: '360px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.375rem', paddingRight: '0.25rem' }}>
        {prospects.map(p => {
          const selected = rosterIds.has(p.player_id);
          const ovrLow = p.public_ovr_band?.[0] ?? '?';
          const ovrHigh = p.public_ovr_band?.[1] ?? '?';
          return (
            <div
              key={p.player_id}
              onClick={() => toggleProspect(p.player_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.625rem 0.875rem',
                background: selected ? 'rgba(34,211,238,0.06)' : '#0f172a',
                border: selected ? '1px solid rgba(34,211,238,0.4)' : '1px solid #1e293b',
                borderRadius: '4px',
                cursor: (!selected && rosterIds.size >= 10) ? 'not-allowed' : 'pointer',
                opacity: (!selected && rosterIds.size >= 10) ? 0.4 : 1,
                transition: 'border-color 0.12s, background 0.12s',
                flexShrink: 0,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: selected ? '#67e8f9' : '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {p.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.125rem' }}>
                  {p.hometown}
                  {p.public_archetype && <span style={{ color: '#475569' }}> · {p.public_archetype}</span>}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0, marginLeft: '1rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="dm-data" style={{ fontWeight: 800, color: selected ? '#22d3ee' : '#94a3b8', fontSize: '0.9375rem' }}>
                    {ovrLow}–{ovrHigh}
                  </div>
                  <div style={{ fontSize: '0.5625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#475569' }}>OVR</div>
                </div>
                <div style={{ width: '18px', height: '18px', borderRadius: '9999px', border: selected ? '2px solid #22d3ee' : '2px solid #334155', background: selected ? 'rgba(34,211,238,0.15)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  {selected && <span style={{ color: '#22d3ee', fontSize: '0.625rem', lineHeight: 1 }}>✓</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <ActionButton variant="secondary" onClick={onBack} disabled={creating}>Back</ActionButton>
        <ActionButton
          variant="primary"
          onClick={() => onCommit(Array.from(rosterIds))}
          disabled={rosterIds.size < 6 || creating}
        >
          {creating ? 'Creating…' : `Commit Roster (${rosterIds.size}/10)`}
        </ActionButton>
        {rosterIds.size < 6 && rosterIds.size > 0 && (
          <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>Need {needed} more</span>
        )}
      </div>
    </div>
  );
}

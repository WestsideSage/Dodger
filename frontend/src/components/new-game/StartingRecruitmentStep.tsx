import { useState, useEffect } from 'react';
import { ActionButton } from '../ui';

export function StartingRecruitmentStep({ 
  onCommit, 
  onBack, 
  creating 
}: { 
  onCommit: (ids: string[]) => void, 
  onBack: () => void, 
  creating: boolean 
}) {
  const [prospects, setProspects] = useState<any[]>([]);
  const [rosterIds, setRosterIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch('/api/saves/starting-prospects')
      .then(r => r.json())
      .then(d => setProspects(d.prospects));
  }, []);

  const toggleProspect = (id: string) => {
    const next = new Set(rosterIds);
    if (next.has(id)) next.delete(id);
    else if (next.size < 10) next.add(id);
    setRosterIds(next);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <h2>Build a Program: Recruit Roster ({rosterIds.size}/10)</h2>
      <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {prospects.map(p => (
          <div key={p.player_id} className="dm-panel" style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', border: rosterIds.has(p.player_id) ? '2px solid #22d3ee' : '1px solid #1e293b', cursor: 'pointer' }} onClick={() => toggleProspect(p.player_id)}>
            <div>
              <div style={{ fontWeight: 700 }}>{p.name}</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{p.hometown} · {p.public_archetype}</div>
            </div>
            <div style={{ textAlign: 'right', fontWeight: 800, color: '#22d3ee' }}>
              {p.public_ovr_band[0]}-{p.public_ovr_band[1]}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <ActionButton onClick={onBack} disabled={creating}>Back</ActionButton>
        <ActionButton onClick={() => onCommit(Array.from(rosterIds))} disabled={rosterIds.size < 6 || creating}>
           {creating ? 'Creating...' : 'Commit Roster'}
        </ActionButton>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { ActionButton } from '../ui';

export function ProspectCard({ prospect, budget, onAction }: { prospect: any, budget: any, onAction: () => void }) {
  const [loading, setLoading] = useState(false);

  const doAction = (verb: string) => {
    setLoading(true);
    fetch(`/api/recruiting/${verb}/${prospect.player_id}`, { method: 'POST' })
      .then(res => {
        if (!res.ok) return res.json().then(d => { throw new Error(d.detail); });
        return res.json();
      })
      .then(() => onAction())
      .catch(err => alert(err.message))
      .finally(() => setLoading(false));
  };

  const canScout = budget.scout[0] < budget.scout[1];
  const canContact = budget.contact[0] < budget.contact[1];
  const canVisit = budget.visit[0] < budget.visit[1];

  return (
    <div className="dm-panel" style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ margin: 0 }}>{prospect.name}</h3>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{prospect.hometown} · {prospect.public_archetype}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#22d3ee' }}>{prospect.public_ovr_band[0]}-{prospect.public_ovr_band[1]}</div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700 }}>Fit: <span style={{ color: '#10b981' }}>STRONG</span></div>
        </div>
      </div>
      
      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <ActionButton disabled={loading || !canScout} onClick={() => doAction('scout')}>Scout</ActionButton>
        <ActionButton disabled={loading || !canContact} onClick={() => doAction('contact')}>Contact</ActionButton>
        <ActionButton disabled={loading || !canVisit} onClick={() => doAction('visit')}>Visit</ActionButton>
      </div>
    </div>
  );
}

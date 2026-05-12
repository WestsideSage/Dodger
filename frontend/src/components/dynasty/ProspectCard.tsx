import { useState } from 'react';
import type { DynastyOfficeResponse } from '../../types';
import { ActionButton } from '../ui';

type RecruitingProspect = DynastyOfficeResponse['recruiting']['prospects'][number];
type RecruitingBudget = DynastyOfficeResponse['recruiting']['budget'];

export function ProspectCard({
  prospect,
  budget,
  onAction,
}: {
  prospect: RecruitingProspect;
  budget: RecruitingBudget;
  onAction: () => void;
}) {
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
  const low = prospect.public_ovr_band?.[0] ?? '?';
  const high = prospect.public_ovr_band?.[1] ?? '?';

  return (
    <article
      className="dm-panel"
      style={{
        marginBottom: '0.8rem',
        padding: 0,
        overflow: 'hidden',
        borderLeft: '3px solid #22d3ee',
        background: 'linear-gradient(90deg, rgba(34,211,238,0.08), transparent 26rem), #0f172a',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '1rem', padding: '1rem 1.1rem 0.85rem' }}>
        <div style={{ minWidth: 0 }}>
          <p className="dm-kicker" style={{ marginBottom: '0.35rem' }}>Recruit Target</p>
          <h3 style={{ margin: 0, color: '#fff', fontSize: '1.05rem', lineHeight: 1.2 }}>{prospect.name}</h3>
          <p style={{ margin: '0.3rem 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
            {prospect.hometown} - {prospect.public_archetype}
          </p>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div className="dm-data" style={{ fontSize: '1.45rem', fontWeight: 900, color: '#22d3ee', lineHeight: 1 }}>
            {low}-{high}
          </div>
          <div style={{ marginTop: '0.3rem', fontSize: '0.72rem', fontWeight: 800, color: '#10b981', textTransform: 'uppercase' }}>
            Strong fit
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', borderTop: '1px solid #1e293b', padding: '0.85rem 1.1rem 1rem' }}>
        <ActionButton disabled={loading || !canScout} onClick={() => doAction('scout')}>Scout</ActionButton>
        <ActionButton disabled={loading || !canContact} onClick={() => doAction('contact')}>Contact</ActionButton>
        <ActionButton disabled={loading || !canVisit} onClick={() => doAction('visit')}>Visit</ActionButton>
      </div>
    </article>
  );
}

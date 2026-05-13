import { ActionButton } from '../ui';
import type { DynastyOfficeResponse } from '../../types';

type StaffCandidate = DynastyOfficeResponse['staff_market']['candidates'][number];

export function StaffMarketModal({ candidates, onHire, onClose }: { candidates: StaffCandidate[], onHire: (id: string) => void, onClose: () => void }) {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="dm-panel" style={{ width: '600px', maxHeight: '80vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <h2>Staff Market</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>✕</button>
        </div>
        {candidates.map(c => (
          <div key={c.candidate_id} style={{ padding: '1rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 700 }}>{c.name}</div>
              <div style={{ fontSize: '0.75rem', color: '#22d3ee' }}>{c.department.toUpperCase()}</div>
              {c.effect_lanes.map((l: string) => <div key={l} style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{l}</div>)}
            </div>
            <ActionButton onClick={() => onHire(c.candidate_id)}>Hire</ActionButton>
          </div>
        ))}
      </div>
    </div>
  );
}

import { TermTip } from '../../legibility';
import type { TermId } from '../../legibility';
import { ActionButton } from '../ui';
import type { DynastyOfficeResponse } from '../../types';

type StaffCandidate = DynastyOfficeResponse['staff_market']['candidates'][number];

const KNOWN_STAFF_TERM_IDS = [
  'staff.training', 'staff.tactics', 'staff.conditioning',
  'staff.medical', 'staff.scouting', 'staff.culture',
] as const;

function staffTermId(department: string): TermId | null {
  const id = `staff.${department}`;
  return (KNOWN_STAFF_TERM_IDS as readonly string[]).includes(id) ? id as TermId : null;
}

export function StaffMarketModal({
  candidates,
  onHire,
  onClose,
}: {
  candidates: StaffCandidate[];
  onHire: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.8)', zIndex: 100,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div className="dm-panel" style={{ width: '600px', maxHeight: '80vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <p className="dm-kicker">Program Staff</p>
            <h2 style={{ margin: '0.25rem 0 0', color: '#fff' }}>Staff Market</h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.25rem' }}
            aria-label="Close staff market"
          >
            X
          </button>
        </div>
        <p style={{ fontSize: '0.68rem', color: '#94a3b8', margin: '0 0 1rem 0' }}>
          Hiring immediately replaces the current department head. Candidates refresh each offseason.
        </p>
        {candidates.map((c) => {
          const tid = staffTermId(c.department);
          const deptLabel = c.department.replace(/^\w/, (ch) => ch.toUpperCase());
          return (
            <div
              key={c.candidate_id}
              style={{ padding: '1rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', gap: '1rem' }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>{c.name}</div>
                <div style={{ fontSize: '0.75rem', color: '#22d3ee', marginBottom: '0.35rem' }}>
                  {tid ? (
                    <TermTip term={tid}>{deptLabel.toUpperCase()}</TermTip>
                  ) : (
                    deptLabel.toUpperCase()
                  )}
                </div>
                {c.effect_lanes.map((lane: string) => (
                  <div key={lane} style={{ fontSize: '0.65rem', color: '#94a3b8', lineHeight: 1.35 }}>
                    {lane}
                  </div>
                ))}
              </div>
              <ActionButton onClick={() => onHire(c.candidate_id)}>Hire</ActionButton>
            </div>
          );
        })}
        {candidates.length === 0 && (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.84rem' }}>
            No candidates are available this period.
          </div>
        )}
      </div>
    </div>
  );
}

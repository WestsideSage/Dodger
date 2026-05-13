import type { Aftermath } from '../../../types';

export function StandingsShift({ shifts }: { shifts: Aftermath['standings_shift'] }) {
  return (
    <div className="dm-panel">
      <p className="dm-kicker">League Table Shifts</p>
      {shifts.length === 0 ? (
        <p>No significant rank changes in the top table.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {shifts.map((s, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>{s.club_name}</span>
              <span>
                {s.old_rank} → <b>{s.new_rank}</b> {s.new_rank < s.old_rank ? <span style={{ color: '#10b981' }}>↑</span> : <span style={{ color: '#f43f5e' }}>↓</span>}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useApiResource } from '../../hooks/useApiResource';
import type { StandingsResponse } from '../../types';

export function ProgramStatusStrip() {
  const { data } = useApiResource<StandingsResponse>('/api/standings');

  const userRow = data?.standings.find(r => r.is_user_club);
  const rank = userRow ? data!.standings.findIndex(r => r.is_user_club) + 1 : null;
  const total = data?.standings.length ?? 0;

  const pctColor = userRow
    ? userRow.wins > userRow.losses ? '#10b981' : userRow.wins < userRow.losses ? '#f43f5e' : '#94a3b8'
    : '#64748b';

  return (
    <div className="dm-panel command-program-status" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem' }}>
      <div>
        <p className="dm-kicker">Your Program</p>
        <h3 className="dm-panel-title" style={{ margin: 0, fontSize: '1.25rem' }}>Season Status</h3>
      </div>

      <div style={{ display: 'flex', gap: '3rem', alignItems: 'center' }}>
        {userRow ? (
          <>
            {/* Rank + points */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {rank !== null && (
                <div>
                  <span className="dm-kicker" style={{ display: 'block' }}>League Rank</span>
                  <span className="dm-data" style={{ color: rank <= 2 ? '#22d3ee' : '#e2e8f0', fontWeight: 800, fontSize: '1.25rem' }}>
                    #{rank} <span style={{ fontSize: '0.75rem', color: '#64748b' }}>of {total}</span>
                  </span>
                </div>
              )}
              <div>
                <span className="dm-kicker" style={{ display: 'block' }}>Points</span>
                <span className="dm-data" style={{ color: pctColor, fontWeight: 800, fontSize: '1.25rem' }}>{userRow.points}</span>
                {userRow.elimination_differential !== 0 && (
                  <span style={{ color: userRow.elimination_differential > 0 ? '#10b981' : '#f43f5e', marginLeft: '0.5rem', fontSize: '0.75rem', fontWeight: 700 }}>
                    {userRow.elimination_differential > 0 ? '+' : ''}{userRow.elimination_differential} diff
                  </span>
                )}
              </div>
            </div>

            {/* W-L-D row */}
            <div style={{ display: 'flex', gap: '1.25rem', borderLeft: '1px solid #1e293b', paddingLeft: '3rem' }}>
              {[
                { label: 'Wins', value: userRow.wins, color: '#10b981' },
                { label: 'Losses', value: userRow.losses, color: '#f43f5e' },
                { label: 'Ties', value: userRow.draws, color: '#94a3b8' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ textAlign: 'center' }}>
                  <div className="dm-data" style={{ fontSize: '1.25rem', fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
                  <div style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', marginTop: '0.25rem' }}>{label}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p style={{ fontSize: '0.8125rem', color: '#64748b', margin: 0 }}>Loading...</p>
        )}
      </div>
    </div>
  );
}

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
    <div className="dm-panel" style={{ flex: 4 }}>
      <div className="dm-panel-header">
        <p className="dm-kicker">Program</p>
        <h3 className="dm-panel-title">Status</h3>
      </div>

      <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
        {userRow ? (
          <>
            {/* W-L-D row */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {[
                { label: 'Wins', value: userRow.wins, color: '#10b981' },
                { label: 'Losses', value: userRow.losses, color: '#f43f5e' },
                { label: 'Ties', value: userRow.draws, color: '#94a3b8' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ textAlign: 'center' }}>
                  <div className="dm-data" style={{ fontSize: '1.5rem', fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
                  <div style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', marginTop: '0.25rem' }}>{label}</div>
                </div>
              ))}
            </div>

            {/* Rank + points */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {rank !== null && (
                <div style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>
                  <span className="dm-kicker">Rank </span>
                  <span className="dm-data" style={{ color: rank <= 2 ? '#22d3ee' : '#e2e8f0', fontWeight: 700 }}>
                    #{rank}
                  </span>
                  <span style={{ color: '#475569' }}> of {total}</span>
                </div>
              )}
              <div style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>
                <span className="dm-kicker">Pts </span>
                <span className="dm-data" style={{ color: pctColor, fontWeight: 700 }}>{userRow.points}</span>
                {userRow.elimination_differential !== 0 && (
                  <span style={{ color: userRow.elimination_differential > 0 ? '#10b981' : '#f43f5e', marginLeft: '0.5rem', fontSize: '0.75rem' }}>
                    {userRow.elimination_differential > 0 ? '+' : ''}{userRow.elimination_differential} diff
                  </span>
                )}
              </div>
            </div>
          </>
        ) : (
          <p style={{ fontSize: '0.8125rem', color: '#64748b', margin: 0 }}>Loading…</p>
        )}

        {/* Quick nav */}
        <div style={{ borderTop: '1px solid #1e293b', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          {[
            { href: '?tab=standings', label: 'Standings' },
            { href: '?tab=roster', label: 'Roster' },
            { href: '?tab=dynasty', label: 'Dynasty Office' },
          ].map(({ href, label }) => (
            <a
              key={href}
              href={href}
              style={{ fontSize: '0.75rem', color: '#64748b', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.375rem' }}
              onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = '#94a3b8'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = '#64748b'; }}
            >
              <span style={{ fontSize: '0.5rem' }}>▶</span>{label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

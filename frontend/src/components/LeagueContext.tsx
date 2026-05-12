import type { StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
import { RecentMatchesSidebar } from './standings/RecentMatchesSidebar';

// ─── helpers ────────────────────────────────────────────────────────────────

function pct(wins: number, losses: number, draws: number): string {
  const played = wins + losses + draws;
  if (played === 0) return '.000';
  const val = (wins + draws * 0.5) / played;
  return val === 1 ? '1.000' : val.toFixed(3).replace(/^0/, '');
}

function gb(leaderWins: number, leaderLosses: number, wins: number, losses: number): string {
  const diff = (leaderWins - wins - (leaderLosses - losses)) / 2;
  if (diff <= 0) return '—';
  return diff % 1 === 0 ? String(diff) : diff.toFixed(1);
}

// ─── Standings ───────────────────────────────────────────────────────────────

export function Standings() {
  const { data, error, loading } = useApiResource<StandingsResponse>('/api/standings');

  if (error) return <StatusMessage title="Standings unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading standings">Updating the table.</StatusMessage>;
  if (!data) return <StatusMessage title="No standings">No standings data returned.</StatusMessage>;

  const rows = data.standings;
  const leader = rows[0];

  const handleRowClick = (teamId: string) => {
    window.location.assign(`#?tab=dynasty&subtab=history&team_id=${teamId}`);
  };

  return (
    <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-start' }}>
      <div className="dm-panel" style={{ flex: 1 }}>
        <div className="dm-panel-header">
          <p className="dm-kicker">League Office</p>
          <h2 className="dm-panel-title">Standings</h2>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="dm-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: '2rem', textAlign: 'center' }}>#</th>
                <th>Club</th>
                <th style={{ textAlign: 'right' }}>
                  <span className="dm-desktop-only">Wins</span>
                  <span className="dm-mobile-only">W</span>
                </th>
                <th style={{ textAlign: 'right' }}>
                  <span className="dm-desktop-only">Losses</span>
                  <span className="dm-mobile-only">L</span>
                </th>
                <th style={{ textAlign: 'right' }}>
                  <span className="dm-desktop-only">Ties</span>
                  <span className="dm-mobile-only">T</span>
                </th>
                <th style={{ textAlign: 'right' }}>
                   <span className="dm-desktop-only">Points</span>
                   <span className="dm-mobile-only">Pts</span>
                </th>
                <th style={{ textAlign: 'right' }}>Win Rate</th>
                <th style={{ textAlign: 'right' }}>Games Back</th>
                <th style={{ textAlign: 'right' }}>
                   <span className="dm-desktop-only">Elim Differential</span>
                   <span className="dm-mobile-only">Diff</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const winPct = pct(row.wins, row.losses, row.draws);
                const gamesBack = leader
                  ? gb(leader.wins, leader.losses, row.wins, row.losses)
                  : '—';
                const diffSign = row.elimination_differential > 0 ? '+' : '';
                const diffColor =
                  row.elimination_differential > 0
                    ? '#10b981'
                    : row.elimination_differential < 0
                    ? '#f43f5e'
                    : '#64748b';

                return (
                  <tr
                    key={row.club_id}
                    onClick={() => handleRowClick(row.club_id)}
                    style={{
                      cursor: 'pointer',
                      background: row.is_user_club ? 'rgba(34,211,238,0.1)' : undefined,
                      borderLeft: row.is_user_club ? '2px solid #22d3ee' : undefined
                    }}
                  >
                    {/* Rank */}
                    <td
                      className="dm-data"
                      style={{ textAlign: 'center', color: '#64748b', width: '2rem' }}
                    >
                      {i + 1}
                    </td>

                    {/* Club name */}
                    <td style={{ fontWeight: 600, color: '#fff', fontFamily: 'var(--font-body)' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                        {row.club_name}
                        {i === 0 && (
                          <span className="dm-badge dm-badge-cyan">1st</span>
                        )}
                        {row.is_user_club && (
                          <span className="dm-badge dm-badge-slate">You</span>
                        )}
                      </span>
                    </td>

                    {/* W */}
                    <td className="dm-data" style={{ textAlign: 'right', color: '#10b981' }}>
                      {row.wins}
                    </td>

                    {/* L */}
                    <td className="dm-data" style={{ textAlign: 'right', color: '#f43f5e' }}>
                      {row.losses}
                    </td>

                    {/* D */}
                    <td className="dm-data" style={{ textAlign: 'right', color: '#94a3b8' }}>
                      {row.draws}
                    </td>

                    {/* Pts */}
                    <td
                      className="dm-data"
                      style={{
                        textAlign: 'right',
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                      }}
                    >
                      {row.points}
                    </td>

                    {/* Win rate */}
                    <td className="dm-data" style={{ textAlign: 'right', color: '#cbd5e1' }}>
                      {winPct}
                    </td>

                    {/* Games back */}
                    <td className="dm-data" style={{ textAlign: 'right', color: '#64748b' }}>
                      {gamesBack}
                    </td>

                    {/* Elim Diff */}
                    <td className="dm-data" style={{ textAlign: 'right', color: diffColor, fontWeight: 600 }}>
                      {diffSign}{row.elimination_differential}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      
      <RecentMatchesSidebar matches={data.recent_matches || []} />
    </div>
  );
}

import type { StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';

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

  return (
    <div className="dm-panel">
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
              <th style={{ textAlign: 'right' }}>W</th>
              <th style={{ textAlign: 'right' }}>L</th>
              <th style={{ textAlign: 'right' }}>D</th>
              <th style={{ textAlign: 'right' }}>Pts</th>
              <th style={{ textAlign: 'right' }}>PCT</th>
              <th style={{ textAlign: 'right' }}>GB</th>
              <th style={{ textAlign: 'right' }}>Diff</th>
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
                  style={
                    row.is_user_club
                      ? { background: 'rgba(148,163,184,0.07)' }
                      : undefined
                  }
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

                  {/* PCT */}
                  <td className="dm-data" style={{ textAlign: 'right', color: '#cbd5e1' }}>
                    {winPct}
                  </td>

                  {/* GB */}
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
  );
}

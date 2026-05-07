import type { NewsResponse, ScheduleResponse, StandingsResponse } from '../types';
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

function scheduleStatusBadge(status: string): { label: string; cls: string } {
  const s = status.toLowerCase();
  if (s.includes('complete') || s.includes('played') || s.includes('final')) {
    return { label: 'Final', cls: 'dm-badge dm-badge-emerald' };
  }
  if (s.includes('live') || s.includes('progress')) {
    return { label: 'Live', cls: 'dm-badge dm-badge-cyan' };
  }
  return { label: status.replaceAll('_', ' '), cls: 'dm-badge dm-badge-amber' };
}

function newsTagBadgeClass(tag: string): string {
  const t = tag.toLowerCase();
  if (t.includes('injur') || t.includes('retire')) return 'dm-badge dm-badge-rose';
  if (t.includes('win') || t.includes('victory') || t.includes('signed')) return 'dm-badge dm-badge-emerald';
  if (t.includes('trade') || t.includes('transfer')) return 'dm-badge dm-badge-amber';
  if (t.includes('record') || t.includes('milestone')) return 'dm-badge dm-badge-cyan';
  return 'dm-badge dm-badge-slate';
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

// ─── Schedule ────────────────────────────────────────────────────────────────

export function Schedule() {
  const { data, error, loading } = useApiResource<ScheduleResponse>('/api/schedule');

  if (error) return <StatusMessage title="Schedule unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading schedule">Collecting fixtures.</StatusMessage>;
  if (!data) return <StatusMessage title="No schedule">No schedule data returned.</StatusMessage>;

  const userMatches = data.schedule.filter(r => r.is_user_match).length;
  const played = data.schedule.filter(r => {
    const s = r.status.toLowerCase();
    return s.includes('complete') || s.includes('played') || s.includes('final');
  }).length;

  return (
    <div className="dm-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">League Office</p>
        <h2 className="dm-panel-title">Schedule</h2>
        <div style={{ display: 'flex', gap: '2rem', marginTop: '0.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.125rem' }}>
            <span className="dm-data" style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
              {data.schedule.length}
            </span>
            <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', fontFamily: 'var(--font-display)' }}>
              Matches
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.125rem' }}>
            <span className="dm-data" style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
              {played}
            </span>
            <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', fontFamily: 'var(--font-display)' }}>
              Played
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.125rem' }}>
            <span className="dm-data" style={{ fontSize: '1rem', fontWeight: 600, color: '#94a3b8' }}>
              {userMatches}
            </span>
            <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', fontFamily: 'var(--font-display)' }}>
              Your Games
            </span>
          </div>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="dm-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th style={{ width: '3.5rem' }}>Week</th>
              <th>Home</th>
              <th style={{ color: '#64748b' }}>Away</th>
              <th style={{ textAlign: 'right', width: '5rem' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.schedule.map(row => {
              const badge = scheduleStatusBadge(row.status);
              const isCompleted =
                row.status.toLowerCase().includes('complete') ||
                row.status.toLowerCase().includes('played') ||
                row.status.toLowerCase().includes('final');

              return (
                <tr
                  key={row.match_id}
                  style={{
                    opacity: isCompleted ? 1 : 0.8,
                    background: row.is_user_match
                      ? 'rgba(148,163,184,0.06)'
                      : undefined,
                  }}
                >
                  {/* Week */}
                  <td className="dm-data" style={{ color: '#64748b', width: '3.5rem' }}>
                    W{row.week}
                  </td>

                  {/* Home */}
                  <td style={{ color: '#fff', fontWeight: 600, fontFamily: 'var(--font-body)' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
                      {row.home_club_name}
                      {row.is_user_match && (
                        <span className="dm-badge dm-badge-slate" style={{ fontSize: '0.5rem' }}>
                          Your Match
                        </span>
                      )}
                    </span>
                  </td>

                  {/* Away */}
                  <td style={{ color: '#94a3b8', fontFamily: 'var(--font-body)' }}>
                    <span style={{ fontSize: '0.6875rem', color: '#475569', marginRight: '0.375rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      vs
                    </span>
                    {row.away_club_name}
                  </td>

                  {/* Status badge */}
                  <td style={{ textAlign: 'right', width: '5rem' }}>
                    <span className={badge.cls}>{badge.label}</span>
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

// ─── NewsWire ────────────────────────────────────────────────────────────────

export function NewsWire() {
  const { data, error, loading } = useApiResource<NewsResponse>('/api/news');

  if (error) return <StatusMessage title="News unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading wire">Checking league headlines.</StatusMessage>;
  if (!data) return <StatusMessage title="No news">No news data returned.</StatusMessage>;

  return (
    <div className="dm-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">League Wire</p>
        <h2 className="dm-panel-title">News</h2>
      </div>

      {data.items.length === 0 ? (
        <div
          className="dm-telemetry-row"
          style={{ padding: '1rem 0.75rem', color: '#475569', fontSize: '0.875rem', fontFamily: 'var(--font-body)' }}
        >
          Season headlines will populate after match reports.
        </div>
      ) : (
        <div
          className="dm-telemetry"
          style={{ border: 'none', background: 'transparent' }}
        >
          {data.items.map((item, index) => (
            <div
              key={`${item.tag}-${item.match_id ?? item.player_id ?? index}`}
              className="dm-telemetry-row"
              style={{ paddingTop: '1rem', paddingBottom: '1rem' }}
            >
              {/* Tag badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                <span className={newsTagBadgeClass(item.tag)}>{item.tag}</span>
              </div>

              {/* Headline text */}
              <p style={{ margin: 0, color: '#cbd5e1', fontSize: '0.875rem', lineHeight: 1.6, fontFamily: 'var(--font-body)' }}>
                {item.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

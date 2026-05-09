export function RecentMatchesSidebar({ matches }: { matches: any[] }) {
  if (!matches || matches.length === 0) return null;
  
  return (
    <div className="dm-panel" style={{ flex: '0 0 300px' }}>
      <div className="dm-panel-header">
        <p className="dm-kicker">Around the League</p>
        <h2 className="dm-panel-title" style={{ fontSize: '1rem' }}>Recent Results</h2>
      </div>
      <div className="dm-section">
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {matches.map(m => (
            <li key={m.match_id} style={{ padding: '0.75rem 0', borderBottom: '1px solid #1e293b' }}>
              <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Week {m.week}</div>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0' }}>{m.summary}</div>
              <div style={{ fontSize: '0.75rem', color: '#22d3ee', marginTop: '0.125rem' }}>Winner: {m.winner_name}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

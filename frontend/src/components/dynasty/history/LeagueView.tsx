import { useEffect, useState } from 'react';

export function LeagueView() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch('/api/history/league')
      .then(res => res.json())
      .then(setData);
  }, []);

  if (!data) return <div>Loading league history...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="dm-panel">
        <p className="dm-kicker">Program Directory</p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {data.directory.map((c: any) => (
            <div key={c.club_id} style={{ padding: '0.5rem', border: '1px solid #334155', borderRadius: '4px', cursor: 'pointer' }}>
              {c.name}
            </div>
          ))}
        </div>
      </div>
      <div className="dm-panel">
        <p className="dm-kicker">Dynasty Rankings</p>
        {data.dynasty_rankings.length === 0 ? <p>No rankings established yet.</p> : <ul>{data.dynasty_rankings.map((r: any, i: number) => <li key={i}>{r}</li>)}</ul>}
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <div className="dm-panel" style={{ flex: 1 }}>
          <p className="dm-kicker">All-Time Records</p>
          {data.records.length === 0 ? <p>No records set.</p> : <ul>{data.records.map((r: any, i: number) => <li key={i}>{r.holder_id} - {r.record_value}</li>)}</ul>}
        </div>
        <div className="dm-panel" style={{ flex: 1 }}>
          <p className="dm-kicker">Hall of Fame</p>
          {data.hof.length === 0 ? <p>No inductees yet.</p> : <ul>{data.hof.map((h: any, i: number) => <li key={i}>{h.name}</li>)}</ul>}
        </div>
      </div>
    </div>
  );
}

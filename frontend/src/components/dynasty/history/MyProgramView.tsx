import { useEffect, useState } from 'react';

export function MyProgramView({ clubId }: { clubId: string }) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`/api/history/my-program?club_id=${clubId}`)
      .then(res => res.json())
      .then(setData);
  }, [clubId]);

  if (!data) return <div>Loading program history...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="dm-panel">
        <p className="dm-kicker">Hero Strip</p>
        <h3>How it started ↔ How it finished</h3>
      </div>
      <div className="dm-panel">
        <p className="dm-kicker">Milestone Timeline</p>
        <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto' }}>
          {data.timeline.map((item: any, i: number) => (
            <div key={i} style={{ padding: '0.5rem', border: '1px solid #334155', borderRadius: '4px' }}>
              <div>{item.year}</div>
              <div>{item.event}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <div className="dm-panel" style={{ flex: 1 }}>
          <p className="dm-kicker">Alumni Lineage</p>
          {data.alumni.length === 0 ? <p>No departed players yet.</p> : <ul>{data.alumni.map((a: any) => <li key={a.id}>{a.name}</li>)}</ul>}
        </div>
        <div className="dm-panel" style={{ flex: 1 }}>
          <p className="dm-kicker">Banner Shelf</p>
          {data.banners.length === 0 ? <p>No banners yet.</p> : <ul>{data.banners.map((b: any) => <li key={b.id}>{b.name}</li>)}</ul>}
        </div>
      </div>
    </div>
  );
}

import type { Aftermath } from '../../../types';

export function PlayerGrowthBlock({ deltas }: { deltas: Aftermath['player_growth_deltas'] }) {
  return (
    <div className="dm-panel">
      <p className="dm-kicker">Player Development</p>
      {deltas.length === 0 ? (
        <p>No attribute growth detected this week.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
          {deltas.map((d, i) => (
            <div key={i} style={{ padding: '0.5rem', border: '1px solid #1e293b', borderRadius: '4px' }}>
              <div style={{ fontWeight: 700 }}>{d.player_name}</div>
              <div style={{ fontSize: '0.875rem', color: '#22d3ee' }}>
                {d.attribute}: <span style={{ color: '#10b981' }}>↑{d.delta}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

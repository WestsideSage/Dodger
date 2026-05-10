interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

const TIER_COLOR: Record<string, string> = {
  Elite: '#10b981',
  High: '#3b82f6',
  Solid: '#94a3b8',
  Limited: '#64748b',
  Unknown: '#475569',
};

export function AlumniLineage({ alumni }: { alumni: AlumnusEntry[] }) {
  if (alumni.length === 0) {
    return (
      <p style={{ color: '#475569', fontSize: '0.8rem' }}>No departed players yet.</p>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      {alumni.map((a) => {
        const tierColor = TIER_COLOR[a.potential_tier] ?? '#475569';
        return (
          <div
            key={a.id}
            style={{
              border: '1px solid #1e293b',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              background: '#0a1628',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.3rem' }}>
              <span style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '0.9rem' }}>{a.name}</span>
              <span style={{ fontSize: '0.65rem', color: '#475569' }}>
                {a.seasons_played} season{a.seasons_played !== 1 ? 's' : ''}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              {a.career_elims} elims · {a.championships} title{a.championships !== 1 ? 's' : ''}
              {a.ovr_final ? ` · OVR ${a.ovr_final}` : ''}
            </div>
            <div style={{ fontSize: '0.68rem', color: tierColor, fontWeight: 600 }}>
              {a.potential_tier} potential
            </div>
          </div>
        );
      })}
    </div>
  );
}

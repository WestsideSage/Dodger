export function CredibilityStrip({ credibility }: { credibility: any }) {
  return (
    <div className="dm-panel" style={{ flex: '0 0 200px' }}>
      <p className="dm-kicker">Program Credibility</p>
      <div style={{ fontSize: '2rem', fontWeight: 900, color: '#22d3ee' }}>Tier {credibility.grade}</div>
      <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Score: {credibility.score}</p>
      <div style={{ marginTop: '1rem' }}>
        {credibility.evidence.map((e: string, i: number) => (
          <div key={i} style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>• {e}</div>
        ))}
      </div>
    </div>
  );
}

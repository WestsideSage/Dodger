export function SimTransition() {
  return (
    <div className="dm-transition-overlay fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem', height: '300px' }}>
      <div className="dm-spinner" style={{ width: '40px', height: '40px', border: '4px solid #334155', borderTop: '4px solid #22d3ee', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
      <p className="dm-kicker" style={{ fontSize: '0.75rem', letterSpacing: '0.2em', color: '#64748b' }}>Simulating…</p>
      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

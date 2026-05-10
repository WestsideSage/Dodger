import { useEffect } from 'react';

export function SimTransition({ onComplete, isFast }: { onComplete: () => void, isFast: boolean }) {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const duration = prefersReducedMotion ? 800 : (isFast ? 1500 : 4000);
    const t = setTimeout(onComplete, duration);
    return () => clearTimeout(t);
  }, [onComplete, isFast]);

  return (
    <div className="dm-transition-overlay fade-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
      <div className="dm-spinner" style={{ width: '40px', height: '40px', border: '4px solid #334155', borderTop: '4px solid #22d3ee', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

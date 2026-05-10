import { useEffect, useState } from 'react';
import { ActionButton, PageHeader } from '../ui';

export function CeremonyShell({ 
  title, 
  eyebrow, 
  description, 
  stages, 
  renderStage, 
  onComplete 
}: { 
  title: string, 
  eyebrow: string, 
  description: string, 
  stages: number, 
  renderStage: (stage: number) => React.ReactNode, 
  onComplete: () => void 
}) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (stage >= stages) return;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const duration = prefersReducedMotion ? 10 : 2000;
    const t = setTimeout(() => setStage(s => s + 1), duration);
    return () => clearTimeout(t);
  }, [stage, stages]);

  useEffect(() => {
    const skip = (e: KeyboardEvent | MouseEvent) => {
      if (e.type === 'keydown' && (e as KeyboardEvent).code !== 'Space') return;
      setStage(stages);
    };
    window.addEventListener('keydown', skip);
    window.addEventListener('click', skip);
    return () => {
      window.removeEventListener('keydown', skip);
      window.removeEventListener('click', skip);
    };
  }, [stages]);

  return (
    <div className="dm-ceremony" style={{ minHeight: '600px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
         {renderStage(stage)}
      </div>
      {stage >= stages && (
        <div style={{ textAlign: 'center', marginTop: 'auto', paddingBottom: '2rem' }}>
          <ActionButton variant="primary" onClick={onComplete}>Continue</ActionButton>
        </div>
      )}
    </div>
  );
}

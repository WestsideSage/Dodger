import { useEffect, useState } from 'react';
import { ActionButton, PageHeader } from '../ui';

export function CeremonyShell({ 
  title, 
  eyebrow, 
  description, 
  stages, 
  renderStage, 
  onComplete,
  actionLabel = 'Continue',
  actionDescription = 'Continue to the next offseason beat.',
  isActing = false,
}: { 
  title: string, 
  eyebrow: string, 
  description: string, 
  stages: number, 
  renderStage: (stage: number) => React.ReactNode, 
  onComplete: () => void,
  actionLabel?: string,
  actionDescription?: string,
  isActing?: boolean,
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
    <div className="dm-ceremony" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
         {renderStage(stage)}
      </div>
      {stage >= stages && (
        <div className="dm-panel command-action-bar" style={{ position: 'sticky', bottom: '1rem', marginTop: 'auto' }}>
          <div>
            <p className="dm-kicker">Ceremony Control</p>
            <p>{actionDescription}</p>
          </div>
          <div className="command-action-buttons">
            <ActionButton variant="primary" onClick={onComplete} disabled={isActing}>
              {isActing ? 'Continuing...' : actionLabel}
            </ActionButton>
          </div>
        </div>
      )}
    </div>
  );
}

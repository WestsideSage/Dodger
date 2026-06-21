import { useEffect, useState } from 'react';
import { ActionButton, PageHeader } from '../../ui';
import styles from './CeremonyShell.module.css';

// WT-21 wrap-not-rewrite assessment: CeremonyShell is a healthy surface and is
// neither a dialog nor a radiogroup. Its only candidate for the shared
// StatusMessage primitive is the transient skip-hint line below, but wrapping
// it would restyle the healthy action bar (StatusMessage carries its own
// panel chrome) and duplicate the existing "Ceremony Control" kicker — a
// contrived wrap that buys no real a11y win. Per the STOP-CONDITION, the
// skip / reduced-motion effects are left exactly as-is. The only change made
// here is a non-visual role="status" on the existing hint <p> so the
// animation-done -> action-available transition is announced politely.
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
  beatIndex,
  totalBeats,
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
  /** 0-based beat position — when provided (with totalBeats) the header
      shows the same progress pips as the structured beats, so the whole
      offseason sequence reads as one ceremony. */
  beatIndex?: number,
  totalBeats?: number,
}) {
  const [stage, setStage] = useState(0);
  const animating = stage < stages;
  const showProgress = typeof beatIndex === 'number' && typeof totalBeats === 'number' && totalBeats > 0;

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
    <div className={`dm-ceremony ${styles.ceremony}`}>
      <PageHeader
        eyebrow={showProgress ? `Offseason Beat ${(beatIndex as number) + 1}/${totalBeats} · ${eyebrow}` : eyebrow}
        title={title}
        description={description}
        stats={showProgress ? (
          <div className="command-offseason-progress" aria-label="Offseason beat progress">
            {Array.from({ length: totalBeats as number }).map((_, index) => (
              <span
                key={index}
                className={
                  index <= (beatIndex as number)
                    ? 'command-offseason-progress-step command-offseason-progress-step-active'
                    : 'command-offseason-progress-step'
                }
              />
            ))}
          </div>
        ) : undefined}
      />
      <div className={`dm-ceremony-stage ${styles.stage}`}>
         {renderStage(stage)}
      </div>
      <div className="dm-panel command-action-bar" style={{ position: 'sticky', bottom: '1rem', marginTop: 'auto' }}>
        <div>
          <p className="dm-kicker">Ceremony Control</p>
          <p role="status">{animating ? 'Press Space or click anywhere to skip animation.' : actionDescription}</p>
        </div>
        <div className="command-action-buttons">
          <ActionButton
            variant="primary"
            onClick={animating ? () => setStage(stages) : onComplete}
            disabled={isActing}
          >
            {isActing ? 'Continuing...' : animating ? 'Skip Reveal' : actionLabel}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

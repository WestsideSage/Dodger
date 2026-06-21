import type { Aftermath } from '../../../types';
import styles from './aftermathCards.module.css';

/**
 * WT-32: the "Manager Lesson" — an ADJACENT card to the Primary Factor, shown
 * ONLY when the backend surfaces `manager_lesson` (i.e. the Primary Factor was
 * inconclusive on a close loss OR an even, close draw). The Primary Factor
 * answers "what decided the match?"; this answers the player's other question,
 * "what could *I* have changed?", strictly from controllable prep. The title
 * and sentence copy are backend-authored and already result-aware (a draw is
 * never described as a loss), so this card renders them verbatim.
 *
 * Two honest states, visually distinct so the player is never misled:
 *   - `controllable: true`  -> a real lever (gold, actionable, with chips);
 *   - `controllable: false` -> the honest "nothing you controlled would have
 *     changed this" message (muted neutral, no chips, no false call-to-action).
 *
 * It is a sibling of PrimaryFactorCard, NOT a replacement: rendered separately
 * by MatchWeek so the event-derived Primary Factor stands on its own.
 */
export function ManagerLessonCard({
  lesson,
}: {
  lesson: NonNullable<Aftermath['manager_lesson']>;
}) {
  const controllable = lesson.controllable;
  const accentClass = controllable ? styles.factorMedium : styles.factorLow;
  const badgeLabel = controllable ? 'CONTROLLABLE' : 'NOT ON YOU';

  return (
    <div
      data-testid="manager-lesson"
      data-lesson-code={lesson.code}
      data-controllable={controllable ? 'true' : 'false'}
      className={`${styles.factorCard} ${accentClass}`}
    >
      <div className={styles.factorHead}>
        <span className={styles.kicker}>Manager Lesson</span>
        <span data-testid="manager-lesson-badge" className={styles.factorBadge}>
          {badgeLabel}
        </span>
      </div>
      <p className={styles.factorTitle}>{lesson.title}</p>
      <p className={styles.factorSentence}>{lesson.sentence}</p>
      {lesson.evidence_chips.length > 0 && (
        <div className={styles.factorChips}>
          {lesson.evidence_chips.map((chip, index) => (
            <span key={`${index}-${chip.slice(0, 8)}`} data-testid="manager-lesson-chip" className={styles.factorChip}>
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

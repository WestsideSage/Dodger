import styles from './aftermathCards.module.css';

interface NarrativeBeatsLike {
  was_shutout: boolean;
  largest_deficit: number;
}

export function ComebackCard({
  text,
  narrativeBeats,
}: {
  text: string;
  narrativeBeats?: NarrativeBeatsLike;
}) {
  // Task 3 (2026-05-28 playtest-fixes): never render the comeback card
  // on a shutout, or on a match where the player team never trailed.
  // The backend already suppresses the comeback moment in those cases,
  // but the frontend is the last line of defence — if a stale Comeback
  // moment slips through, the card must self-suppress on narrative
  // beats rather than show "clawed it back" on a 3-0 win.
  if (narrativeBeats) {
    if (narrativeBeats.was_shutout) return null;
    if (narrativeBeats.largest_deficit === 0) return null;
  }
  return (
    <article data-testid="comeback-card" className={styles.comeback}>
      <p className={styles.comebackKicker}>Comeback</p>
      <p className={styles.comebackText}>{text}</p>
    </article>
  );
}

import { ActionButton } from '../../ui';
import styles from './CoachStep.module.css';

const ARCHETYPES: Record<string, { tagline: string; description: string }> = {
  'Tactical Mastermind': {
    tagline: 'The Schemer',
    description: 'Obsesses over game plans and exploits opponent tendencies. Boosts tactical preparation, key-matchup reads, and in-match adjustments.',
  },
  'Recruiting Legend': {
    tagline: 'The Talent Magnet',
    description: 'Commands instant credibility on the prospect trail. Improves recruit interest rates, budget efficiency, and the quality of your incoming class.',
  },
  'Former Player': {
    tagline: 'The Lifer',
    description: 'Earns unconditional trust from the locker room. Drives faster player development, higher morale, and stronger team cohesion under pressure.',
  },
};

export interface CoachForm {
  coach_name: string;
  coach_backstory: string;
}

export function CoachStep({
  coach,
  setCoach,
  onNext,
  onBack,
}: {
  coach: CoachForm;
  setCoach: (v: CoachForm) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const selected = ARCHETYPES[coach.coach_backstory] ?? ARCHETYPES['Tactical Mastermind'];
  const coachReady = Boolean(coach.coach_name.trim());

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <p className={styles.kicker}>Step 2 of 4</p>
        <h2 className={styles.title}>Head Coach</h2>
      </div>

      <div>
        <label htmlFor="coach-name" className={styles.fieldLabel}>
          Coach Name
        </label>
        <input
          id="coach-name"
          type="text"
          placeholder="e.g. Ray Holloway"
          value={coach.coach_name}
          onChange={e => setCoach({ ...coach, coach_name: e.target.value })}
          className={styles.input}
        />
      </div>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Coaching Archetype</legend>
        <div className={styles.archetypeList}>
          {Object.entries(ARCHETYPES).map(([key, arch]) => {
            const isSelected = coach.coach_backstory === key;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setCoach({ ...coach, coach_backstory: key })}
                className={`${styles.archetypeCard} ${isSelected ? styles.archetypeCardSelected : ''}`.trim()}
              >
                <div className={styles.archetypeHead}>
                  <span className={`${styles.archetypeName} ${isSelected ? styles.archetypeNameSelected : ''}`.trim()}>
                    {key}
                  </span>
                  <span className={styles.tagline}>{arch.tagline}</span>
                </div>
                <p className={styles.archetypeDesc}>{arch.description}</p>
              </button>
            );
          })}
        </div>
      </fieldset>

      {coach.coach_name && (
        <div className={styles.summary}>
          <p className={styles.summaryText}>
            <span className={styles.summaryName}>{coach.coach_name}</span>
            {' | '}
            <span className={styles.summaryArchetype}>{coach.coach_backstory}</span>
            {' - '}
            {selected.description}
          </p>
        </div>
      )}

      <div className={styles.actions}>
        <div className={styles.actionRow}>
          <ActionButton variant="secondary" onClick={onBack}>Back</ActionButton>
          <ActionButton variant="primary" onClick={onNext} disabled={!coachReady} aria-describedby="coach-step-help">
            Next: Recruit Roster
          </ActionButton>
        </div>
        {!coachReady && (
          <p id="coach-step-help" className={styles.helperWarning}>
            Enter a coach name to continue.
          </p>
        )}
      </div>
    </div>
  );
}

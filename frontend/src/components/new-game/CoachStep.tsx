import { ActionButton } from '../ui';

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Step 2 of 3</p>
        <h2 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0, fontSize: '1.25rem' }}>
          Head Coach
        </h2>
      </div>

      {/* Coach name */}
      <div>
        <label style={{ display: 'block', fontSize: '0.6875rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', marginBottom: '0.375rem' }}>
          Coach Name
        </label>
        <input
          type="text"
          placeholder="e.g. Ray Holloway"
          value={coach.coach_name}
          onChange={e => setCoach({ ...coach, coach_name: e.target.value })}
          style={{
            width: '100%',
            boxSizing: 'border-box',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '4px',
            padding: '0.5rem 0.75rem',
            color: '#e2e8f0',
            fontSize: '0.875rem',
          }}
        />
      </div>

      {/* Archetype picker */}
      <div>
        <label style={{ display: 'block', fontSize: '0.6875rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', marginBottom: '0.5rem' }}>
          Coaching Archetype
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {Object.entries(ARCHETYPES).map(([key, arch]) => {
            const isSelected = coach.coach_backstory === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setCoach({ ...coach, coach_backstory: key })}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.25rem',
                  padding: '0.875rem 1rem',
                  background: isSelected ? 'rgba(249,115,22,0.08)' : '#0f172a',
                  border: isSelected ? '1px solid rgba(249,115,22,0.4)' : '1px solid #334155',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.875rem', color: isSelected ? '#f97316' : '#e2e8f0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {key}
                  </span>
                  <span className="dm-badge dm-badge-slate" style={{ fontSize: '0.6rem' }}>{arch.tagline}</span>
                </div>
                <p style={{ margin: 0, fontSize: '0.8125rem', color: '#94a3b8', lineHeight: 1.4 }}>{arch.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected summary */}
      {coach.coach_name && (
        <div style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: '4px', padding: '0.75rem 1rem' }}>
          <p style={{ margin: 0, fontSize: '0.8125rem', color: '#94a3b8' }}>
            <span style={{ color: '#f97316', fontWeight: 700 }}>{coach.coach_name}</span>
            {' · '}
            <span style={{ color: '#e2e8f0' }}>{coach.coach_backstory}</span>
            {' — '}
            {selected.description}
          </p>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <ActionButton variant="secondary" onClick={onBack}>Back</ActionButton>
        <ActionButton variant="primary" onClick={onNext} disabled={!coach.coach_name}>
          Next: Recruit Roster
        </ActionButton>
      </div>
    </div>
  );
}

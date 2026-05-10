import { ActionButton } from '../ui';

export function CoachStep({ coach, setCoach, onNext, onBack }: { coach: any, setCoach: (v: any) => void, onNext: () => void, onBack: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <h2>Build a Program: Head Coach</h2>
      <input type="text" placeholder="Coach Name" value={coach.coach_name} onChange={e => setCoach({...coach, coach_name: e.target.value})} style={{ padding: '0.5rem' }} />
      <select value={coach.coach_backstory} onChange={e => setCoach({...coach, coach_backstory: e.target.value})} style={{ padding: '0.5rem' }}>
        <option value="Tactical Mastermind">Tactical Mastermind</option>
        <option value="Recruiting Legend">Recruiting Legend</option>
        <option value="Former Player">Former Player</option>
      </select>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <ActionButton onClick={onBack}>Back</ActionButton>
        <ActionButton onClick={onNext} disabled={!coach.coach_name}>Next: Recruit Roster</ActionButton>
      </div>
    </div>
  );
}

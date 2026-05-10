import { CeremonyShell } from './CeremonyShell';

export function AwardsNight({ beat, onComplete }: { beat: any, onComplete: () => void }) {
  return (
    <CeremonyShell 
      title={beat.title} 
      eyebrow="Ceremony" 
      description="The league gathers to honor the season's best."
      stages={2}
      renderStage={(stage) => (
        <div style={{ textAlign: 'center' }}>
          {stage >= 1 && <div className="fade-in" style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>{beat.body[0]}</div>}
          {stage >= 2 && <div className="fade-in" style={{ fontSize: '2rem', color: '#f97316', fontWeight: 800 }}>{beat.body.slice(1).join(' ')}</div>}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}

export function Graduation({ beat, onComplete }: { beat: any, onComplete: () => void }) {
  return (
    <CeremonyShell 
      title={beat.title} 
      eyebrow="Ceremony" 
      description="Saying goodbye to departing seniors."
      stages={1}
      renderStage={(stage) => (
        <div style={{ textAlign: 'center' }}>
          {stage >= 1 && <div className="fade-in" style={{ fontSize: '1.25rem' }}>{beat.body.join(' ')}</div>}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}

export function CoachingCarousel({ beat, onComplete }: { beat: any, onComplete: () => void }) {
  return (
    <CeremonyShell 
      title={beat.title} 
      eyebrow="Ceremony" 
      description="Staff movements across the league."
      stages={1}
      renderStage={(stage) => (
        <div style={{ textAlign: 'center' }}>
          {stage >= 1 && <div className="fade-in" style={{ fontSize: '1.25rem' }}>{beat.body.join(' ')}</div>}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}

export function SigningDay({ beat, onComplete }: { beat: any, onComplete: () => void }) {
  return (
    <CeremonyShell 
      title={beat.title} 
      eyebrow="Ceremony" 
      description="The nation's top prospects make their commitments."
      stages={1}
      renderStage={(stage) => (
        <div style={{ textAlign: 'center' }}>
          {stage >= 1 && <div className="fade-in" style={{ fontSize: '1.5rem', color: '#22d3ee' }}>{beat.body.join(' ')}</div>}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}

export function NewSeasonEve({ beat, onComplete }: { beat: any, onComplete: () => void }) {
  return (
    <CeremonyShell 
      title={beat.title} 
      eyebrow="Ceremony" 
      description="A new season is upon us."
      stages={2}
      renderStage={(stage) => (
        <div style={{ textAlign: 'center' }}>
          {stage >= 1 && <div className="fade-in" style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>{beat.body[0]}</div>}
          {stage >= 2 && <div className="fade-in" style={{ fontSize: '2rem', color: '#10b981', fontWeight: 800 }}>{beat.body.slice(1).join(' ')}</div>}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}

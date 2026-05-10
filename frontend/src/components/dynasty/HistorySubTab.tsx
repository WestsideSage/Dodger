import { useState } from 'react';
import { MyProgramView } from './history/MyProgramView';
import { LeagueView } from './history/LeagueView';

export function HistorySubTab({ clubId }: { clubId: string }) {
  const [view, setView] = useState<'program' | 'league'>('program');

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <button onClick={() => setView('program')} style={{ background: view === 'program' ? '#1e293b' : 'transparent', border: '1px solid #334155', padding: '0.5rem 1rem', borderRadius: '4px', color: '#e2e8f0', cursor: 'pointer' }}>My Program</button>
        <button onClick={() => setView('league')} style={{ background: view === 'league' ? '#1e293b' : 'transparent', border: '1px solid #334155', padding: '0.5rem 1rem', borderRadius: '4px', color: '#e2e8f0', cursor: 'pointer' }}>League</button>
      </div>

      {view === 'program' && <MyProgramView clubId={clubId} />}
      {view === 'league' && <LeagueView />}
    </div>
  );
}

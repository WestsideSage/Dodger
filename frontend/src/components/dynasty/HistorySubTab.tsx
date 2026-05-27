import { useState } from 'react';
import { MyProgramView } from './history/MyProgramView';
import { LeagueView } from './history/LeagueView';

export function HistorySubTab({ clubId, isSelf = true }: { clubId: string; isSelf?: boolean }) {
  const [view, setView] = useState<'program' | 'league'>('program');
  const programLabel = isSelf ? 'My Program' : 'Program';

  return (
    <div className="do-tab-content">
      <div className="do-hist-filters">
        <div className="filters">
          <button
            className={`do-board-filter ${view === 'program' ? 'is-active' : ''}`}
            onClick={() => setView('program')}
            type="button"
          >
            {programLabel}
          </button>
          <button
            className={`do-board-filter ${view === 'league' ? 'is-active' : ''}`}
            onClick={() => setView('league')}
            type="button"
          >
            League
          </button>
        </div>
        <span className="do-board-meta">
          {view === 'program' ? 'Program archive view' : 'League archive view'}
        </span>
      </div>

      {view === 'program' && <MyProgramView clubId={clubId} isSelf={isSelf} />}
      {view === 'league' && <LeagueView />}
    </div>
  );
}

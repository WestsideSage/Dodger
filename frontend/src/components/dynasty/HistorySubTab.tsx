import { useState } from 'react';
import { MyProgramView } from './history/MyProgramView';
import { LeagueView } from './history/LeagueView';
import styles from './history/HistorySubTab.module.css';

export function HistorySubTab({ clubId, isSelf = true }: { clubId: string; isSelf?: boolean }) {
  const [view, setView] = useState<'program' | 'league'>('program');
  const programLabel = isSelf ? 'My Program' : 'Program';

  return (
    <div className={styles.content}>
      <div className={styles.filters}>
        <div className={styles.filterRow}>
          <button
            className={`${styles.filter} ${view === 'program' ? styles.filterActive : ''}`}
            onClick={() => setView('program')}
            type="button"
          >
            {programLabel}
          </button>
          <button
            className={`${styles.filter} ${view === 'league' ? styles.filterActive : ''}`}
            onClick={() => setView('league')}
            type="button"
          >
            League
          </button>
        </div>
        <span className={styles.meta}>
          {view === 'program' ? 'Program archive view' : 'League archive view'}
        </span>
      </div>

      {view === 'program' && <MyProgramView clubId={clubId} isSelf={isSelf} />}
      {view === 'league' && <LeagueView />}
    </div>
  );
}

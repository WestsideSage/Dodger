import { useState } from 'react';
import type { DivisionStandingsBlock } from '../../types';
import { Truncate } from '../../ui';
import styles from './PyramidPanel.module.css';

const formatDiff = (value: number) => (value > 0 ? `+${value}` : String(value));

// V23: the world beyond your table. One compact card per division — the
// player's division is the main table above, so this panel is for watching
// the rest of the pyramid (and the Circuit) live their own seasons.
export function PyramidPanel({
  divisions,
  isOfficial,
  onClubClick,
}: {
  divisions: DivisionStandingsBlock[];
  isOfficial: boolean;
  onClubClick: (clubId: string, clubName: string) => void;
}) {
  const userDivision = divisions.find((division) => division.is_user_division);
  const [activeId, setActiveId] = useState<string>(userDivision?.division_id ?? divisions[0]?.division_id ?? '');
  const active = divisions.find((division) => division.division_id === activeId) ?? divisions[0];
  if (!active) return null;
  const relegationCount = active.movement?.relegation_count ?? 0;

  return (
    <div className={styles.panel}>
      <div className={styles.panelHead}>
        <span className={styles.kicker}>The Pyramid</span>
        <h3>World Standings</h3>
      </div>
      <div role="tablist" aria-label="Divisions" className={styles.tabs}>
        {divisions.map((division) => (
          <button
            key={division.division_id}
            type="button"
            role="tab"
            aria-selected={division.division_id === active.division_id}
            className={`${styles.tab} ${division.division_id === active.division_id ? styles.tabActive : ''}`.trim()}
            onClick={() => setActiveId(division.division_id)}
          >
            {division.short_name}
            {division.is_user_division ? ' ★' : ''}
          </button>
        ))}
      </div>
      <div className={styles.body}>
        <div className={styles.divisionTitle}>
          <strong>{active.name}</strong>
          {active.is_user_division && <span className={styles.yourDivisionTag}>YOUR DIVISION</span>}
        </div>
        <div className={styles.list}>
          {active.standings.map((standing, index) => {
            const inRelegation = relegationCount > 0 && index >= active.standings.length - relegationCount;
            return (
              <div
                key={standing.club_id}
                className={styles.row}
                onClick={() => onClubClick(standing.club_id, standing.club_name)}
                role="button"
                tabIndex={0}
                // Worded so the main table's "Open X program history" is NOT
                // a substring (Playwright role-name matching is substring
                // based — the duplicate label was a strict-mode ambiguity).
                aria-label={`${standing.club_name} program history — ${active.name} table`}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onClubClick(standing.club_id, standing.club_name);
                  }
                }}
              >
                <span className={styles.from}>#{index + 1}</span>
                <div className={styles.rowBody}>
                  <Truncate className={styles.who}>
                    {standing.club_name}
                    {standing.is_user_club ? ' ★' : ''}
                  </Truncate>
                  <span className={styles.note}>
                    {standing.wins}-{standing.losses}-{standing.draws} · {standing.points} pts ·{' '}
                    {formatDiff(isOfficial ? (standing.game_point_differential ?? 0) : standing.elimination_differential)} diff
                  </span>
                </div>
                {inRelegation && <span className={styles.drop}>DROP</span>}
              </div>
            );
          })}
        </div>
        {active.movement?.summary && <p className={styles.summary}>{active.movement.summary}</p>}
      </div>
    </div>
  );
}

import { useState } from 'react';
import { useApiResource } from '../../../hooks/useApiResource';
import { StatusMessage } from '../../../ui';
import { ProgramModal } from './ProgramModal';
import { formatRecordLabel, formatSeasonLabel, humanizeHistoryToken } from './formatters';
import { EmptyState } from '../../../legibility/EmptyState';
import styles from './LeagueView.module.css';

interface LeagueData {
  directory: Array<{ club_id: string; name: string }>;
  dynasty_rankings: Array<{
    club_id: string;
    club_name: string;
    championships: number;
    longest_win_streak: number;
  }>;
  records: Array<{
    record_type: string;
    holder_id: string;
    record_value: number;
    set_in_season: string;
    /** PT4-07: the persisted record payload carries the holder's real
        display name — render it instead of humanizing the raw id. */
    record?: { holder_name?: string; detail?: string };
  }>;
  hof: Array<{
    player_id: string;
    player_name: string;
    induction_season: string;
    career_elims: number;
    championships: number;
    seasons_played: number;
  }>;
  rivalries: Array<{
    club_a: string;
    club_b: string;
    a_wins: number;
    b_wins: number;
    draws: number;
    meetings: number;
  }>;
  /** V23: the World Championship roll, newest first (pyramid saves only). */
  worlds?: Array<{
    season_id: string;
    champion_club_id: string;
    champion_name: string;
    runner_up_club_id: string | null;
    runner_up_name: string | null;
  }>;
}

export function LeagueView() {
  const { data, error, loading } = useApiResource<LeagueData>('/api/history/league');
  const [modal, setModal] = useState<{ clubId: string; clubName: string } | null>(null);

  if (error) {
    return (
      <StatusMessage title="League archive unavailable" tone="danger">
        {error}
      </StatusMessage>
    );
  }
  if (loading) {
    return <StatusMessage title="Loading league archive">Building the league-wide history board.</StatusMessage>;
  }
  if (!data) return null;

  const topDynasty = data.dynasty_rankings[0] ?? null;
  const topRivalry = data.rivalries[0] ?? null;

  return (
    <div className={styles.content}>
      <div className={styles.glance}>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Programs Tracked</span>
          <span className={styles.cellVal}>{data.directory.length}</span>
          <span className={styles.cellTrend}>Open any club archive from the directory below</span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Dynasty Leader</span>
          <span className={styles.cellVal}>{topDynasty ? topDynasty.club_name : 'None Yet'}</span>
          <span className={`${styles.cellTrend} ${topDynasty && topDynasty.championships > 0 ? styles.cellTrendOk : ''}`}>
            {topDynasty
              ? `${topDynasty.championships} title${topDynasty.championships === 1 ? '' : 's'} · longest streak ${topDynasty.longest_win_streak}`
              : 'First champion has not been crowned yet'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Records Logged</span>
          <span className={styles.cellVal}>{data.records.length}</span>
          <span className={styles.cellTrend}>
            {data.records.length > 0
              ? 'League marks are being tracked'
              : 'Records will appear after the first stat milestones'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Hall of Fame</span>
          <span className={styles.cellVal}>{data.hof.length}</span>
          <span className={styles.cellTrend}>
            {data.hof.length > 0 ? 'Legacy lane is active' : 'First inductee class is still being earned'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Top Rivalry</span>
          <span className={styles.cellVal}>{topRivalry ? `${topRivalry.meetings}` : '0'}</span>
          <span className={styles.cellTrend}>
            {topRivalry ? `${topRivalry.club_a} vs ${topRivalry.club_b}` : 'No rivalry board yet'}
          </span>
        </div>
      </div>

      <section className={styles.card}>
        <div className={styles.cardHead}>
          <span className={styles.cardKicker}>Program Directory</span>
          <h3 className={styles.cardTitle}>Open any club archive</h3>
        </div>
        <div className={styles.directory}>
          {data.directory.map((club) => (
            <button
              key={club.club_id}
              className={styles.directoryBtn}
              onClick={() => setModal({ clubId: club.club_id, clubName: club.name })}
              type="button"
            >
              {club.name}
            </button>
          ))}
        </div>
      </section>

      <div className={styles.grid}>
        {data.worlds && data.worlds.length > 0 && (
          <section className={styles.card}>
            <div className={styles.cardHead}>
              <span className={styles.cardKicker}>World Championship</span>
              <h3 className={styles.cardTitle}>The summit, season by season</h3>
            </div>
            <div className={styles.list}>
              {data.worlds.map((entry) => (
                <div key={entry.season_id} className={styles.row}>
                  <div className={styles.main}>
                    <strong className={styles.rowName}>★ {entry.champion_name}</strong>
                    <span className={styles.meta}>
                      {formatSeasonLabel(entry.season_id)}
                      {entry.runner_up_name ? ` — beat ${entry.runner_up_name} in the final` : ''}
                    </span>
                  </div>
                  <div className={styles.side}>
                    <span className={`${styles.badge} ${styles.badgeBrick}`}>WORLDS</span>
                    <span className={styles.note}>Premier top two vs the International Circuit's best.</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>Dynasty Rankings</span>
            <h3 className={styles.cardTitle}>Program standard-setters</h3>
          </div>
          {data.dynasty_rankings.length > 0 ? (
            <div className={styles.list}>
              {data.dynasty_rankings.map((entry, index) => (
                <div key={entry.club_id} className={styles.row}>
                  <div className={styles.main}>
                    <strong className={styles.rowName}>#{index + 1} {entry.club_name}</strong>
                    <span className={styles.meta}>{entry.championships} title{entry.championships === 1 ? '' : 's'}</span>
                  </div>
                  <div className={styles.side}>
                    <span className={`${styles.badge} ${styles.badgeBrick}`}>Win streak {entry.longest_win_streak}</span>
                    <span className={styles.note}>Championship count is the first dynasty tiebreak.</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No dynasty rankings yet"
              body="Rankings appear after the first championship is claimed. Win the league to start the board."
            />
          )}
        </section>

        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>All-Time Records</span>
            <h3 className={styles.cardTitle}>League records board</h3>
          </div>
          {data.records.length > 0 ? (
            <div className={styles.list}>
              {data.records.map((record, index) => (
                <div key={`${record.record_type}-${record.holder_id}-${index}`} className={styles.row}>
                  <div className={styles.main}>
                    <strong className={styles.rowName}>{formatRecordLabel(record.record_type)}</strong>
                    <span className={styles.meta}>
                      {record.record?.holder_name || humanizeHistoryToken(record.holder_id)} - {formatSeasonLabel(record.set_in_season)}
                    </span>
                  </div>
                  <div className={styles.side}>
                    <span className={styles.badge}>{record.record_value}</span>
                    <span className={styles.note}>Current league record holder.</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No league records set"
              body="Individual season-stat records are logged here once the league has enough history to establish a mark."
            />
          )}
        </section>

        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>Hall of Fame</span>
            <h3 className={styles.cardTitle}>Career immortals</h3>
          </div>
          {data.hof.length > 0 ? (
            <div className={styles.list}>
              {data.hof.map((entry) => (
                <div key={entry.player_id} className={styles.row}>
                  <div className={styles.main}>
                    <strong className={styles.rowName}>{entry.player_name}</strong>
                    <span className={styles.meta}>
                      Inducted {formatSeasonLabel(entry.induction_season)} - {entry.seasons_played} season{entry.seasons_played === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div className={styles.side}>
                    <span className={`${styles.badge} ${styles.badgeBrick}`}>{entry.championships} titles</span>
                    <span className={styles.note}>{entry.career_elims} career eliminations</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Hall of Fame is empty"
              body="Players inducted after distinguished careers will appear here. The first class is still being earned."
              icon="🏛️"
            />
          )}
        </section>

        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>Rivalries</span>
            <h3 className={styles.cardTitle}>Heat map of repeat opponents</h3>
          </div>
          {data.rivalries.length > 0 ? (
            <div className={styles.list}>
              {data.rivalries.slice(0, 6).map((rivalry, index) => (
                <div key={`${rivalry.club_a}-${rivalry.club_b}-${index}`} className={styles.row}>
                  <div className={styles.main}>
                    <strong className={styles.rowName}>{rivalry.club_a} vs {rivalry.club_b}</strong>
                    <span className={styles.meta}>
                      {rivalry.a_wins}-{rivalry.b_wins}-{rivalry.draws} across {rivalry.meetings} meetings
                    </span>
                  </div>
                  <div className={styles.side}>
                    <span className={`${styles.badge} ${index === 0 ? styles.badgeBrick : styles.badgeOutline}`}>
                      {index === 0 ? 'Top heat' : 'Tracked'}
                    </span>
                    <span className={styles.note}>Most played club pairings rise to the top.</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No rivalries tracked yet"
              body="Club pairings that meet repeatedly rise to the top. A few more seasons will surface the heat maps."
            />
          )}
        </section>
      </div>

      {modal ? (
        <ProgramModal clubId={modal.clubId} clubName={modal.clubName} onClose={() => setModal(null)} />
      ) : null}
    </div>
  );
}

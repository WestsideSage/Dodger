import { useState } from 'react';
import { useApiResource } from '../../../hooks/useApiResource';
import { StatusMessage } from '../../ui';
import { ProgramModal } from './ProgramModal';
import { formatRecordLabel, formatSeasonLabel, humanizeHistoryToken } from './formatters';
import { EmptyState } from '../../../legibility/EmptyState';

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
    <div className="do-tab-content">
      <div className="do-hist-glance">
        <div className="cell">
          <span className="lbl">Programs Tracked</span>
          <span className="val">{data.directory.length}</span>
          <span className="trend">Open any club archive from the directory below</span>
        </div>
        <div className="cell">
          <span className="lbl">Dynasty Leader</span>
          <span className="val">{topDynasty ? topDynasty.club_name : 'None Yet'}</span>
          <span className={`trend ${topDynasty && topDynasty.championships > 0 ? 'ok' : ''}`}>
            {topDynasty
              ? `${topDynasty.championships} title${topDynasty.championships === 1 ? '' : 's'} · longest streak ${topDynasty.longest_win_streak}`
              : 'First champion has not been crowned yet'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Records Logged</span>
          <span className="val">{data.records.length}</span>
          <span className="trend">
            {data.records.length > 0
              ? 'League marks are being tracked'
              : 'Records will appear after the first stat milestones'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Hall of Fame</span>
          <span className="val">{data.hof.length}</span>
          <span className="trend">
            {data.hof.length > 0 ? 'Legacy lane is active' : 'First inductee class is still being earned'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Top Rivalry</span>
          <span className="val">{topRivalry ? `${topRivalry.meetings}` : '0'}</span>
          <span className="trend">
            {topRivalry ? `${topRivalry.club_a} vs ${topRivalry.club_b}` : 'No rivalry board yet'}
          </span>
        </div>
      </div>

      <section className="dm-panel do-hist-card">
        <div className="do-hist-card-head">
          <span className="dm-kicker">Program Directory</span>
          <h3>Open any club archive</h3>
        </div>
        <div className="do-hist-directory">
          {data.directory.map((club) => (
            <button
              key={club.club_id}
              className="do-hist-directory-btn"
              onClick={() => setModal({ clubId: club.club_id, clubName: club.name })}
              type="button"
            >
              {club.name}
            </button>
          ))}
        </div>
      </section>

      <div className="do-hist-grid">
        {data.worlds && data.worlds.length > 0 && (
          <section className="dm-panel do-hist-card">
            <div className="do-hist-card-head">
              <span className="dm-kicker">World Championship</span>
              <h3>The summit, season by season</h3>
            </div>
            <div className="do-hist-list">
              {data.worlds.map((entry) => (
                <div key={entry.season_id} className="do-hist-list-row">
                  <div className="main">
                    <strong>★ {entry.champion_name}</strong>
                    <span className="meta">
                      {formatSeasonLabel(entry.season_id)}
                      {entry.runner_up_name ? ` — beat ${entry.runner_up_name} in the final` : ''}
                    </span>
                  </div>
                  <div className="side">
                    <span className="dm-badge dm-badge-amber">WORLDS</span>
                    <span className="note">Premier top two vs the International Circuit's best.</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">Dynasty Rankings</span>
            <h3>Program standard-setters</h3>
          </div>
          {data.dynasty_rankings.length > 0 ? (
            <div className="do-hist-list">
              {data.dynasty_rankings.map((entry, index) => (
                <div key={entry.club_id} className="do-hist-list-row">
                  <div className="main">
                    <strong>#{index + 1} {entry.club_name}</strong>
                    <span className="meta">{entry.championships} title{entry.championships === 1 ? '' : 's'}</span>
                  </div>
                  <div className="side">
                    <span className="dm-badge dm-badge-amber">Win streak {entry.longest_win_streak}</span>
                    <span className="note">Championship count is the first dynasty tiebreak.</span>
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

        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">All-Time Records</span>
            <h3>League records board</h3>
          </div>
          {data.records.length > 0 ? (
            <div className="do-hist-list">
              {data.records.map((record, index) => (
                <div key={`${record.record_type}-${record.holder_id}-${index}`} className="do-hist-list-row">
                  <div className="main">
                    <strong>{formatRecordLabel(record.record_type)}</strong>
                    <span className="meta">{humanizeHistoryToken(record.holder_id)} - {formatSeasonLabel(record.set_in_season)}</span>
                  </div>
                  <div className="side">
                    <span className="dm-badge dm-badge-cyan">{record.record_value}</span>
                    <span className="note">Current league record holder.</span>
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

        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">Hall of Fame</span>
            <h3>Career immortals</h3>
          </div>
          {data.hof.length > 0 ? (
            <div className="do-hist-list">
              {data.hof.map((entry) => (
                <div key={entry.player_id} className="do-hist-list-row">
                  <div className="main">
                    <strong>{entry.player_name}</strong>
                    <span className="meta">
                      Inducted {formatSeasonLabel(entry.induction_season)} - {entry.seasons_played} season{entry.seasons_played === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div className="side">
                    <span className="dm-badge dm-badge-amber">{entry.championships} titles</span>
                    <span className="note">{entry.career_elims} career eliminations</span>
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

        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">Rivalries</span>
            <h3>Heat map of repeat opponents</h3>
          </div>
          {data.rivalries.length > 0 ? (
            <div className="do-hist-list">
              {data.rivalries.slice(0, 6).map((rivalry, index) => (
                <div key={`${rivalry.club_a}-${rivalry.club_b}-${index}`} className="do-hist-list-row">
                  <div className="main">
                    <strong>{rivalry.club_a} vs {rivalry.club_b}</strong>
                    <span className="meta">
                      {rivalry.a_wins}-{rivalry.b_wins}-{rivalry.draws} across {rivalry.meetings} meetings
                    </span>
                  </div>
                  <div className="side">
                    <span className={`dm-badge ${index === 0 ? 'dm-badge-rose' : 'dm-badge-slate'}`}>
                      {index === 0 ? 'Top heat' : 'Tracked'}
                    </span>
                    <span className="note">Most played club pairings rise to the top.</span>
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

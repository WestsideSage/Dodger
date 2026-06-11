import React, { useMemo, useState } from 'react';
import type { PlayoffBracketResponse, RecentMatchSummary, StandingRow, StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
import { PlayoffBracket } from './standings/PlayoffBracket';
import { ProgramModal } from './dynasty/history/ProgramModal';
import { TermTip, EmptyState, CLUB_ARCHETYPE_TERM } from '../legibility';

type RankedStanding = StandingRow & {
  rank: number;
};

type ParsedMatchSummary = {
  awayClubName: string;
  awayScore: string;
  homeClubName: string;
  homeScore: string;
};

const DEFAULT_APPROACH = 'Balanced';

const parseMatchSummary = (summary: string): ParsedMatchSummary | null => {
  const match = summary.match(/^(.+?)\s+(\d+)-(\d+)\s+(.+)$/);
  if (!match) return null;
  const [, homeClubName, homeScore, awayScore, awayClubName] = match;
  return { homeClubName, homeScore, awayClubName, awayScore };
};

const formatDiff = (value: number) => (value > 0 ? `+${value}` : String(value));

const normalizeApproach = (value: string | null | undefined) => {
  const next = value?.trim();
  return next && next.length > 0 ? next : DEFAULT_APPROACH;
};

// The "Plan" badge shows a club's program intent using the command-center
// display vocabulary the backend now emits (bug #7): Balanced, Aggressive,
// Control, Defensive, plus the AI-only raw "Develop Youth". Tone the badge to
// that exact vocabulary. (Substring checks keep this resilient if the backend
// passthrough ever surfaces another raw intent.)
const approachToneClass = (value: string | null | undefined) => {
  const normalized = normalizeApproach(value).toLowerCase();
  if (normalized.includes('aggressive')) return 'dm-badge-amber';
  if (normalized.includes('defensive') || normalized.includes('control')) return 'dm-badge-violet';
  if (normalized.includes('develop')) return 'dm-badge-emerald';
  if (normalized.includes('balanced')) return 'dm-badge-cyan';
  return 'dm-badge-slate';
};

const NeedState = ({
  action,
  helper,
  outcome,
}: {
  action: string;
  helper: string;
  outcome: string;
}) => (
  <>
    <div className="need-row">
      <span className="need-action">{action}</span>
      <span className="need-arrow">-&gt;</span>
      <span className="need-outcome">{outcome}</span>
    </div>
    <p className="need-helper">{helper}</p>
  </>
);

const FormStub = ({ label }: { label: string | null | undefined }) => (
  <div className="ls-form-with-label">
    <span className="lbl-mini">Plan</span>
    <span className={`dm-badge ${approachToneClass(label)}`}>{normalizeApproach(label)}</span>
  </div>
);

const DiffBar = ({ diff, max }: { diff: number; max: number }) => {
  const pct = max === 0 ? 0 : Math.min(100, (Math.abs(diff) / max) * 100);
  const isPositive = diff >= 0;

  return (
    <div className="ls-diff-cell">
      <div className="ls-diff-bar">
        <span className="axis" />
        <span
          className={`fill ${isPositive ? 'pos' : 'neg'}`}
          style={{
            left: isPositive ? '50%' : `calc(50% - ${pct / 2}%)`,
            width: `${pct / 2}%`,
          }}
        />
      </div>
      <span className={`ls-diff-val ${isPositive ? 'pos' : 'neg'}`}>{formatDiff(diff)}</span>
    </div>
  );
};

const buildNeedCopy = (
  us: RankedStanding,
  leader: RankedStanding,
  cutoffTeam: RankedStanding,
  playoffLine: number,
  gamesRemaining: number,
  diffLabel: string,
) => {
  // "Games to play" (byes excluded), matching the command center's count so
  // the two surfaces never disagree on how much season is left.
  const weeksRemaining = gamesRemaining;
  const cushion = Math.max(0, us.points - cutoffTeam.points);
  const pointsBack = Math.max(0, cutoffTeam.points - us.points);
  const leaderGap = Math.max(0, leader.points - us.points);

  if (us.rank === 1) {
    return {
      action: 'Hold Lead',
      outcome: 'Stay #1',
      helper:
        weeksRemaining > 0
          ? `You are pacing the table with ${weeksRemaining} to play. Keep the edge on ${diffLabel}.`
          : `The table lead is yours. ${diffLabel.charAt(0).toUpperCase()}${diffLabel.slice(1)} is the live tiebreaker.`,
    };
  }

  if (us.rank <= playoffLine) {
    return {
      action: 'Win Next',
      outcome: `Hold Top ${playoffLine}`,
      helper:
        leaderGap > 0
          ? `You sit ${leaderGap} point${leaderGap === 1 ? '' : 's'} behind #1 and ${cushion} clear of the cut line.`
          : `You are on the line with ${cushion} point${cushion === 1 ? '' : 's'} of breathing room over the bubble.`,
    };
  }

  return {
    action: 'Win Next',
    outcome: `Break Top ${playoffLine}`,
    helper:
      weeksRemaining > 0
        ? `You are ${pointsBack} point${pointsBack === 1 ? '' : 's'} outside the playoff line with ${weeksRemaining} to play to close it.`
        : `You finish ${pointsBack} point${pointsBack === 1 ? '' : 's'} outside the playoff line unless the tiebreak flips.`,
  };
};

const buildRaceSummary = (us: RankedStanding, leader: RankedStanding, cutoffTeam: RankedStanding, playoffLine: number) => {
  if (us.rank === 1) {
    const lead = Math.max(0, us.points - cutoffTeam.points);
    return {
      left: `LEADS BY ${lead}`,
      right: `TOP ${playoffLine} LOCK`,
    };
  }

  if (us.rank <= playoffLine) {
    return {
      left: `${Math.max(0, us.points - cutoffTeam.points)} PTS CUSHION`,
      right: `${Math.max(0, leader.points - us.points)} BACK OF #1`,
    };
  }

  return {
    left: `${Math.max(0, cutoffTeam.points - us.points)} BACK OF CUT`,
    right: `${Math.max(0, leader.points - us.points)} BACK OF #1`,
  };
};

const buildWireRows = (
  recentMatches: RecentMatchSummary[] | undefined,
  userClubName: string,
): React.ReactNode[] | null => {
  if (!recentMatches || recentMatches.length === 0) {
    return null; // caller renders EmptyState
  }

  return recentMatches.map((match) => {
    const parsed = parseMatchSummary(match.summary);
    if (!parsed) {
      return (
        <span key={match.match_id} className="ls-wire-item">
          <b>W{String(match.week).padStart(2, '0')}</b> {match.summary}
        </span>
      );
    }

    const involvesUser = parsed.homeClubName === userClubName || parsed.awayClubName === userClubName;
    const resultTag = match.winner_name === 'Draw' ? 'Draw' : `${parsed.homeClubName} ${parsed.homeScore}-${parsed.awayScore} ${parsed.awayClubName}`;

    return (
      <span
        key={match.match_id}
        className={`ls-wire-item${involvesUser ? ' is-us' : ''}`}
        aria-label={`Week ${match.week}: ${resultTag}`}
      >
        <span className="ls-wire-item-wk">W{String(match.week).padStart(2, '0')}</span>
        <span className="ls-wire-item-score">{resultTag}</span>
        {involvesUser && <span className="ls-wire-item-you" aria-label="your match">★</span>}
      </span>
    );
  });
};

export function Standings() {
  const { data, error, loading } = useApiResource<StandingsResponse>('/api/standings');
  const { data: bracket } = useApiResource<PlayoffBracketResponse>('/api/playoffs/bracket');
  const [modalClub, setModalClub] = useState<{ id: string; name: string } | null>(null);

  const standings = useMemo<RankedStanding[]>(
    () => (data?.standings ?? []).map((standing, index) => ({ ...standing, rank: index + 1 })),
    [data?.standings],
  );

  // V20 §7.3 survivors cleanup: official careers rank on GAME POINTS — the
  // survivor differential is a legacy/rec stat (on officials it only ever
  // held final-game living counts, i.e. noise). Display the differential
  // that actually ranks this career.
  const isOfficial = data?.is_official_career ?? false;
  const diffOf = (standing: StandingRow) =>
    isOfficial ? (standing.game_point_differential ?? 0) : standing.elimination_differential;

  const maxDiff = useMemo(
    () => Math.max(0, ...standings.map((standing) => Math.abs(
      isOfficial ? (standing.game_point_differential ?? 0) : standing.elimination_differential,
    ))),
    [standings, isOfficial],
  );

  if (error) return <StatusMessage title="Standings unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading standings">Updating the table.</StatusMessage>;
  if (!data || standings.length === 0) return <StatusMessage title="No standings">No standings data returned.</StatusMessage>;

  const us = standings.find((standing) => standing.is_user_club) ?? standings[0];
  const leader = standings[0];
  const playoffLine = data.playoff_spots;
  const cutoffTeam = standings.find((standing) => standing.rank === playoffLine + 1) ?? standings[standings.length - 1];
  const isOffseason = data.is_offseason === true;
  // During the playoff phase the bracket above is canon; the regular-season
  // race/need copy is stale and misleading, so it's replaced (Brief 4.6, #4).
  const playoffsActive = bracket?.active === true && !isOffseason;
  const raceSummary = isOffseason
    ? { left: 'SEASON CONCLUDED', right: 'PREPARING FOR NEXT SEASON' }
    : playoffsActive
      ? { left: 'REG. SEASON DONE', right: 'PLAYOFFS LIVE' }
      : buildRaceSummary(us, leader, cutoffTeam, playoffLine);
  const needCopy = isOffseason
    ? {
        action: 'Season Concluded',
        outcome: 'Preparing for Next Season',
        helper: `Final standing: #${us.rank} of ${standings.length}. ${us.wins}-${us.losses}-${us.draws} on the season.`,
      }
    : playoffsActive
      ? {
          action: 'Playoffs',
          outcome: 'Bracket Decides',
          helper: `Regular season finished #${us.rank} of ${standings.length}. The bracket above now decides the title.`,
        }
      : buildNeedCopy(us, leader, cutoffTeam, playoffLine, data.user_games_remaining ?? Math.max(0, data.total_weeks - data.current_week), isOfficial ? 'game-point differential' : 'survivor differential');
  const wireRows = buildWireRows(data.recent_matches, us.club_name);
  const tiebreakRows = standings.slice(0, Math.min(standings.length, playoffLine + 2));

  const allZeroPoints = standings.every((s) => s.points === 0);
  const tiebreakerState: 'hidden' | 'soft' | 'live' =
    isOffseason || playoffsActive
      ? 'hidden'
      : data.current_week <= 1 || allZeroPoints
        ? 'soft'
        : 'live';

  const handleClubModal = (clubId: string, clubName: string) => {
    setModalClub({ id: clubId, name: clubName });
  };

  return (
    <>
      {bracket?.active && <PlayoffBracket data={bracket} />}

      <div className="max-content ls-shell" data-screen-label="04 Standings">
        <div className="ls-glance">
          <div className="ls-glance-cell ls-glance-rank">
            <span className="lbl">Our Rank</span>
            <div className="rank-row">
              <span className="num">{us.rank}</span>
              <span className="suffix">OF {standings.length}</span>
            </div>
            <div className={`trend ${us.rank <= playoffLine ? 'up' : 'down'}`}>
              <span className="arrow">{us.rank <= playoffLine ? '^' : 'v'}</span>
              {isOffseason
                ? `FINAL · SEASON CONCLUDED`
                : playoffsActive
                  ? `REG. SEASON FINAL · #${us.rank} SEED`
                  : us.rank <= playoffLine
                    ? `IN PLAYOFF POSITION — WEEK ${String(data.current_week).padStart(2, '0')}`
                    : `OUTSIDE PLAYOFF LINE — WEEK ${String(data.current_week).padStart(2, '0')}`}
            </div>
          </div>

          <div className="ls-glance-cell ls-glance-record">
            <span className="lbl">Season Record</span>
            <div className="record-row">
              <span className="rec">{us.wins}-{us.losses}-{us.draws}</span>
              <span
                className="diff"
                style={diffOf(us) < 0 ? { color: 'var(--dm-rose)' } : undefined}
              >
                {formatDiff(diffOf(us))}
              </span>
            </div>
            <FormStub label={us.latest_approach} />
          </div>

          <div className="ls-glance-cell ls-glance-race">
            <span className="lbl">Playoff Race</span>
            <div className="race">
              {standings.slice(0, Math.min(standings.length, playoffLine + 1)).map((standing) => (
                <span
                  key={standing.rank}
                  className={`race-pip ${standing.rank <= playoffLine ? 'in' : 'out'} ${standing.is_user_club ? 'us' : ''}`}
                >
                  <span className="rk">{standing.rank}</span>
                </span>
              ))}
            </div>
            <div className="cushion">
              <span className="cushion-pos">{raceSummary.left}</span>
              <span className="cushion-sep">-</span>
              <span className="cushion-back">{raceSummary.right}</span>
            </div>
          </div>

          <div className="ls-glance-cell ls-glance-next">
            <span className="lbl">This Week's Target</span>
            <NeedState action={needCopy.action} outcome={needCopy.outcome} helper={needCopy.helper} />
          </div>
        </div>

        <div className="ls-table-card">
          <div className="ls-table-head">
            <div>
              <span className="dm-kicker">League Office</span>
              <h2 className="ls-table-title">
                {playoffsActive ? 'Final Regular-Season Table' : 'Season Standings'}{' '}
                <span className="ls-subtle">{playoffsActive ? 'Playoffs live above' : 'Regular season'}</span>
              </h2>
            </div>
            <div className="ls-table-meta">
              <span className="dm-badge dm-badge-cyan">WEEK {String(data.current_week).padStart(2, '0')}</span>
              <span className="dm-badge dm-badge-emerald">TOP {playoffLine}</span>
              <span className="dm-badge dm-badge-slate">{standings.length} CLUBS</span>
            </div>
          </div>

          <div className="ls-table-scroll">
            <table className="ls-table">
              <thead>
                <tr>
                  <th className="num">#</th>
                  <th>Club</th>
                  <th className="num">W</th>
                  <th className="num">L</th>
                  <th className="num">D</th>
                  <th className="num">PTS</th>
                  <th>Plan</th>
                  <th>
                    <TermTip term={isOfficial ? 'standings.gp_diff' : 'standings.diff'}>{isOfficial ? 'GP Diff' : 'Survivor Diff'}</TermTip>
                  </th>
                </tr>
              </thead>
              <tbody>
                {standings.map((standing, index) => {
                  const isCutLine = index === playoffLine;
                  return (
                    <React.Fragment key={standing.club_id}>
                      {isCutLine && (
                        <tr className="ls-playoff-line">
                          <td colSpan={8}>
                            <div className="cut-row">
                              <span className="line-bar" />
                              <span className="line-label">Playoff Cut</span>
                              <span className="line-bar" />
                            </div>
                          </td>
                        </tr>
                      )}
                      <tr
                        className={standing.is_user_club ? 'ls-user' : ''}
                        onClick={() => handleClubModal(standing.club_id, standing.club_name)}
                        style={{ cursor: 'pointer' }}
                        role="button"
                        tabIndex={0}
                        aria-haspopup="dialog"
                        aria-label={`Open ${standing.club_name} program history`}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            handleClubModal(standing.club_id, standing.club_name);
                          }
                        }}
                      >
                        <td className="num">
                          <span className={`ls-rank ${standing.rank <= playoffLine ? 'in' : 'out'}`}>{standing.rank}</span>
                        </td>
                        <td>
                          <div className="ls-club">
                            <span className="club-name">{standing.club_name}</span>
                            <div className="ls-subtle" style={{ display: 'block', marginLeft: 0 }}>
                              {(() => {
                                const raw = standing.program_trajectory_label ?? standing.program_archetype ?? '';
                                const archetype = raw.includes(' · ') ? raw.split(' · ').slice(1).join(' · ') : raw;
                                if (!archetype) return null;
                                const termId = CLUB_ARCHETYPE_TERM[archetype];
                                return termId
                                  ? <TermTip term={termId}>{archetype}</TermTip>
                                  : <span>{archetype}</span>;
                              })()}
                            </div>
                          </div>
                        </td>
                        <td className="num"><span className="ls-cell-num">{standing.wins}</span></td>
                        <td className="num"><span className="ls-cell-num muted">{standing.losses}</span></td>
                        <td className="num"><span className="ls-cell-num muted">{standing.draws}</span></td>
                        <td className="num"><span className="ls-cell-num pts">{standing.points}</span></td>
                        <td>
                          <span className={`dm-badge ${approachToneClass(standing.latest_approach)}`}>
                            {normalizeApproach(standing.latest_approach)}
                          </span>
                        </td>
                        <td><DiffBar diff={diffOf(standing)} max={maxDiff} /></td>
                      </tr>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="ls-table-foot">
            <span className="ls-legend-item"><span className="dm-badge dm-badge-cyan">YOU</span> User club row</span>
            <span className="ls-legend-sep">-</span>
            <span className="ls-legend-item"><span className="dm-badge dm-badge-amber">CUT</span> Playoff line</span>
            <span className="ls-legend-sep">-</span>
            <span className="ls-legend-item">
              <TermTip term="standings.playoff_line">Playoff Line</TermTip>
              {' '}— top {playoffLine} advance
            </span>
            <span className="ls-legend-sep">-</span>
            <span className="ls-legend-note">Click any row to open that club's program history.</span>
          </div>
        </div>

        <div className="ls-side">
          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">League Wire</span>
              <h3>Recent Results</h3>
            </div>
            {wireRows === null ? (
              <EmptyState
                title="No results yet"
                body="League Wire updates here after the first week of matches is complete."
                icon="📡"
              />
            ) : (
              <div
                className="ls-wire-ticker"
                role="list"
                aria-label="Recent league results"
                style={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: '0.75rem',
                  overflowX: 'auto',
                  padding: '0.5rem 0.75rem',
                  WebkitOverflowScrolling: 'touch',
                }}
              >
                {wireRows}
              </div>
            )}
          </div>

          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">Tiebreaker Read</span>
              <h3>
                {tiebreakerState === 'hidden'
                  ? 'Race Concluded'
                  : tiebreakerState === 'soft'
                    ? 'Race Developing'
                    : `Top ${playoffLine} Race`}
              </h3>
            </div>
            {tiebreakerState === 'hidden' ? (
              <EmptyState
                title={isOffseason ? 'Season concluded' : 'Bracket is live'}
                body={
                  isOffseason
                    ? 'The regular season is over. See the offseason recap for final standings.'
                    : 'The playoff bracket above is now the deciding surface.'
                }
              />
            ) : tiebreakerState === 'soft' ? (
              <EmptyState
                title="Race not yet meaningful"
                body="No matches have been played. The tiebreaker read will update after Week 1 results are in."
              />
            ) : (
              <div className="ls-tb-list">
                {tiebreakRows.map((standing) => {
                  const isSafe = standing.rank <= playoffLine;
                  return (
                    <div
                      key={`tb-${standing.club_id}`}
                      className="ls-tb-row"
                      onClick={() => handleClubModal(standing.club_id, standing.club_name)}
                      style={{ cursor: 'pointer' }}
                      role="button"
                      tabIndex={0}
                      aria-haspopup="dialog"
                      aria-label={`Open ${standing.club_name} program history`}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          handleClubModal(standing.club_id, standing.club_name);
                        }
                      }}
                    >
                      <span className="ls-tb-from">#{standing.rank}</span>
                      <div className="ls-tb-body">
                        <span className="ls-tb-who">{standing.club_name}</span>
                        <span className="ls-tb-note">
                          {standing.points} pts · {formatDiff(diffOf(standing))} diff
                        </span>
                      </div>
                      <span className={`ls-tb-risk ${isSafe ? 'risk-low' : 'risk-high'}`}>
                        {isSafe ? 'IN' : 'BUBBLE'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
      {modalClub && (
        <ProgramModal
          clubId={modalClub.id}
          clubName={modalClub.name}
          onClose={() => setModalClub(null)}
        />
      )}
    </>
  );
}

import React, { useMemo } from 'react';
import type { PlayoffBracketResponse, RecentMatchSummary, StandingRow, StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
import { PlayoffBracket } from './standings/PlayoffBracket';

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

const approachToneClass = (value: string | null | undefined) => {
  const normalized = normalizeApproach(value).toLowerCase();
  if (normalized.includes('aggressive') || normalized.includes('win now')) return 'dm-badge-amber';
  if (normalized.includes('defensive') || normalized.includes('prepare')) return 'dm-badge-violet';
  if (normalized.includes('balanced') || normalized.includes('mixed')) return 'dm-badge-cyan';
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
  totalWeeks: number,
  currentWeek: number,
) => {
  const weeksRemaining = Math.max(0, totalWeeks - currentWeek);
  const cushion = Math.max(0, us.points - cutoffTeam.points);
  const pointsBack = Math.max(0, cutoffTeam.points - us.points);
  const leaderGap = Math.max(0, leader.points - us.points);

  if (us.rank === 1) {
    return {
      action: 'Hold Lead',
      outcome: 'Stay #1',
      helper:
        weeksRemaining > 0
          ? `You are pacing the table with ${weeksRemaining} week${weeksRemaining === 1 ? '' : 's'} left. Keep the edge on survivor differential.`
          : 'The table lead is yours. Survivor differential is the live tiebreaker.',
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
        ? `You are ${pointsBack} point${pointsBack === 1 ? '' : 's'} outside the playoff line with ${weeksRemaining} week${weeksRemaining === 1 ? '' : 's'} left to close it.`
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
  currentWeek: number,
) => {
  if (!recentMatches || recentMatches.length === 0) {
    return [
      <div key="empty" className="ls-wire-row">
        <span className="ls-wire-week">W{String(currentWeek).padStart(2, '0')}</span>
        <div className="ls-wire-fixture">
          <span className="ls-wire-team home">Season</span>
          <span className="ls-wire-score"><b>OPEN</b></span>
          <span className="ls-wire-team away">Awaiting first result</span>
        </div>
        <span className="ls-wire-tag tag-draw">LIVE</span>
      </div>,
    ];
  }

  return recentMatches.map((match) => {
    const parsed = parseMatchSummary(match.summary);
    if (!parsed) {
      return (
        <div key={match.match_id} className="ls-wire-row">
          <span className="ls-wire-week">W{String(match.week).padStart(2, '0')}</span>
          <div className="ls-wire-fixture">
            <span className="ls-wire-team home">League</span>
            <span className="ls-wire-score"><b>UPDATE</b></span>
            <span className="ls-wire-team away">{match.summary}</span>
          </div>
          <span className="ls-wire-tag tag-draw">NOTE</span>
        </div>
      );
    }

    const involvesUser = parsed.homeClubName === userClubName || parsed.awayClubName === userClubName;
    const tagClass = match.winner_name === 'Draw' ? 'tag-draw' : 'tag-win';

    return (
      <div key={match.match_id} className={`ls-wire-row ${involvesUser ? 'is-us' : ''}`}>
        <span className="ls-wire-week">W{String(match.week).padStart(2, '0')}</span>
        <div className="ls-wire-fixture">
          <span className="ls-wire-team home">{parsed.homeClubName}</span>
          <span className="ls-wire-score">
            <b>{parsed.homeScore}</b>-<b>{parsed.awayScore}</b>
          </span>
          <span className="ls-wire-team away">{parsed.awayClubName}</span>
        </div>
        <span className={`ls-wire-tag ${tagClass}`}>{match.winner_name === 'Draw' ? 'DRAW' : 'WIN'}</span>
      </div>
    );
  });
};

export function Standings() {
  const { data, error, loading } = useApiResource<StandingsResponse>('/api/standings');
  const { data: bracket } = useApiResource<PlayoffBracketResponse>('/api/playoffs/bracket');

  const standings = useMemo<RankedStanding[]>(
    () => (data?.standings ?? []).map((standing, index) => ({ ...standing, rank: index + 1 })),
    [data?.standings],
  );

  const maxDiff = useMemo(
    () => Math.max(0, ...standings.map((standing) => Math.abs(standing.elimination_differential))),
    [standings],
  );

  if (error) return <StatusMessage title="Standings unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading standings">Updating the table.</StatusMessage>;
  if (!data || standings.length === 0) return <StatusMessage title="No standings">No standings data returned.</StatusMessage>;

  const us = standings.find((standing) => standing.is_user_club) ?? standings[0];
  const leader = standings[0];
  const playoffLine = data.playoff_spots;
  const cutoffTeam = standings.find((standing) => standing.rank === playoffLine + 1) ?? standings[standings.length - 1];
  const isOffseason = data.is_offseason === true;
  const raceSummary = isOffseason
    ? { left: 'SEASON CONCLUDED', right: 'PREPARING FOR NEXT SEASON' }
    : buildRaceSummary(us, leader, cutoffTeam, playoffLine);
  const needCopy = isOffseason
    ? {
        action: 'Season Concluded',
        outcome: 'Preparing for Next Season',
        helper: `Final standing: #${us.rank} of ${standings.length}. ${us.wins}-${us.losses}-${us.draws} on the season.`,
      }
    : buildNeedCopy(us, leader, cutoffTeam, playoffLine, data.total_weeks, data.current_week);
  const wireRows = buildWireRows(data.recent_matches, us.club_name, data.current_week);
  const tiebreakRows = standings.slice(0, Math.min(standings.length, playoffLine + 2));

  const handleClubOpen = (clubId: string) => {
    const params = new URLSearchParams(window.location.search);
    params.set('tab', 'dynasty');
    params.set('subtab', 'history');
    params.set('team_id', clubId);
    window.location.assign(`${window.location.pathname}?${params.toString()}`);
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
                : us.rank <= playoffLine
                  ? `ABOVE LINE THROUGH W${String(data.current_week).padStart(2, '0')}`
                  : `CHASE MODE THROUGH W${String(data.current_week).padStart(2, '0')}`}
            </div>
          </div>

          <div className="ls-glance-cell ls-glance-record">
            <span className="lbl">Record - Diff</span>
            <div className="record-row">
              <span className="rec">{us.wins}-{us.losses}-{us.draws}</span>
              <span
                className="diff"
                style={us.elimination_differential < 0 ? { color: 'var(--dm-rose)' } : undefined}
              >
                {formatDiff(us.elimination_differential)}
              </span>
            </div>
            <FormStub label={us.latest_approach} />
          </div>

          <div className="ls-glance-cell ls-glance-race">
            <span className="lbl">Playoff Line - Top {playoffLine}</span>
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
            <span className="lbl">Next Result Needs</span>
            <NeedState action={needCopy.action} outcome={needCopy.outcome} helper={needCopy.helper} />
          </div>
        </div>

        <div className="ls-table-card">
          <div className="ls-table-head">
            <div>
              <span className="dm-kicker">League Office</span>
              <h2 className="ls-table-title">
                Season Standings{' '}
                <span className="ls-subtle">Live season table</span>
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
                  <th>Survivor Diff</th>
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
                        className={standing.is_user_club ? 'ls-user' : undefined}
                        onClick={() => handleClubOpen(standing.club_id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="num">
                          <span className={`ls-rank ${standing.rank <= playoffLine ? 'in' : 'out'}`}>{standing.rank}</span>
                        </td>
                        <td>
                          <div className="ls-club">
                            <span className="club-name">{standing.club_name}</span>
                            <div className="ls-subtle" style={{ display: 'block', marginLeft: 0 }}>
                              {standing.program_trajectory_label ?? standing.program_archetype ?? 'Program track live'}
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
                        <td><DiffBar diff={standing.elimination_differential} max={maxDiff} /></td>
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
            <span className="ls-legend-note">Click a club to open its history lane.</span>
          </div>
        </div>

        <div className="ls-side">
          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">League Wire</span>
              <h3>Recent Results</h3>
            </div>
            <div className="ls-wire-list">{wireRows}</div>
          </div>

          <div className="ls-panel">
            <div className="ls-panel-head">
              <span className="dm-kicker">Tiebreaker Read</span>
              <h3>Top {playoffLine} Race</h3>
            </div>
            <div className="ls-tb-list">
              {tiebreakRows.map((standing) => {
                const isSafe = standing.rank <= playoffLine;
                return (
                  <div
                    key={`tb-${standing.club_id}`}
                    className="ls-tb-row"
                    onClick={() => handleClubOpen(standing.club_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <span className="ls-tb-from">#{standing.rank}</span>
                    <div className="ls-tb-body">
                      <span className="ls-tb-who">{standing.club_name}</span>
                      <span className="ls-tb-note">
                        {standing.points} pts - {formatDiff(standing.elimination_differential)} diff - {normalizeApproach(standing.latest_approach)}
                      </span>
                    </div>
                    <span className={`ls-tb-risk ${isSafe ? 'risk-low' : 'risk-high'}`}>
                      {isSafe ? 'IN' : 'BUBBLE'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

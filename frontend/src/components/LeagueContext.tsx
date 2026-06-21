import React, { useMemo, useState } from 'react';
import type { NewsItem, PlayoffBracketResponse, RecentMatchSummary, StandingRow, StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage, Truncate, Tag } from '../ui';
import type { TagTone } from '../ui';
import { PlayoffBracket } from './standings/PlayoffBracket';
import { PyramidPanel } from './standings/PyramidPanel';
import { ProgramModal } from './dynasty/history/ProgramModal';
import { TermTip, EmptyState, CLUB_ARCHETYPE_TERM } from '../legibility';
import styles from './LeagueContext.module.css';

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
// that exact vocabulary, mapped onto the Floodlight 5-color Tag tones.
// (Substring checks keep this resilient if the backend passthrough ever
// surfaces another raw intent.)
const approachTone = (value: string | null | undefined): TagTone => {
  const normalized = normalizeApproach(value).toLowerCase();
  if (normalized.includes('aggressive')) return 'live';
  if (normalized.includes('defensive') || normalized.includes('control')) return 'out';
  if (normalized.includes('develop')) return 'verified';
  return 'neutral'; // Balanced + any unknown intent
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
    <div className={styles.needRow}>
      <span className={styles.needAction}>{action}</span>
      <span className={styles.needArrow}>-&gt;</span>
      <span className={styles.needOutcome}>{outcome}</span>
    </div>
    <p className={styles.needHelper}>{helper}</p>
  </>
);

const FormStub = ({ label }: { label: string | null | undefined }) => (
  <div className={styles.formWithLabel}>
    <span className={styles.lblMini}>Plan</span>
    <Tag tone={approachTone(label)}>{normalizeApproach(label)}</Tag>
  </div>
);

const DiffBar = ({ diff, max }: { diff: number; max: number }) => {
  const pct = max === 0 ? 0 : Math.min(100, (Math.abs(diff) / max) * 100);
  const isPositive = diff >= 0;

  return (
    <div className={styles.diffCell}>
      <div className={styles.diffBar}>
        <span className={styles.diffAxis} />
        <span
          className={`${styles.diffFill} ${isPositive ? styles.diffFillPos : styles.diffFillNeg}`}
          style={{
            left: isPositive ? '50%' : `calc(50% - ${pct / 2}%)`,
            width: `${pct / 2}%`,
          }}
        />
      </div>
      <span className={`${styles.diffVal} ${isPositive ? styles.diffValPos : styles.diffValNeg}`}>{formatDiff(diff)}</span>
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
        <span key={match.match_id} className={styles.wireItem}>
          <b>W{String(match.week).padStart(2, '0')}</b> {match.summary}
        </span>
      );
    }

    const involvesUser = parsed.homeClubName === userClubName || parsed.awayClubName === userClubName;
    const resultTag = match.winner_name === 'Draw' ? 'Draw' : `${parsed.homeClubName} ${parsed.homeScore}-${parsed.awayScore} ${parsed.awayClubName}`;

    return (
      <span
        key={match.match_id}
        className={`${styles.wireItem} ${involvesUser ? styles.wireItemIsUs : ''}`.trim()}
        aria-label={`Week ${match.week}: ${resultTag}`}
      >
        <span className={styles.wireWk}>W{String(match.week).padStart(2, '0')}</span>
        <span className={styles.wireScore}>{resultTag}</span>
        {involvesUser && <span className={styles.wireYou} aria-label="your match">★</span>}
      </span>
    );
  });
};

// V28: the league news wire — class/event/meta/league_bulletin headlines that
// rode the standings payload. Headlines ride at the FRONT of the ticker (the
// "top of the wire"), tagged by their wire kind (Meta Wire, League Wire, …).
const buildHeadlineRows = (
  headlines: NewsItem[] | null | undefined,
): React.ReactNode[] => {
  if (!headlines || headlines.length === 0) {
    return [];
  }
  return headlines.map((headline, index) => (
    <span
      key={`wire-headline-${index}`}
      className={`${styles.wireItem} ${styles.wireItemIsHeadline}`}
      aria-label={`${headline.tag}: ${headline.text}`}
    >
      <span className={styles.wireWk}>{headline.tag}</span>
      <span className={styles.wireScore}>{headline.text}</span>
    </span>
  ));
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
  // V28: prepend the news-wire headlines (meta/league bulletins, class/event
  // wire) to the recent-results ticker — they ride at the top of the wire.
  const headlineRows = buildHeadlineRows(data.wire_headlines);
  const matchRows = buildWireRows(data.recent_matches, us.club_name);
  const wireRows =
    headlineRows.length === 0 && matchRows === null
      ? null
      : [...headlineRows, ...(matchRows ?? [])];
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

      <div className={styles.shell} data-screen-label="04 Standings">
        <div className={styles.glance}>
          <div className={styles.glanceCell}>
            <span className={styles.lbl}>Our Rank</span>
            <div className={styles.rankRow}>
              <span className={styles.num}>{us.rank}</span>
              <span className={styles.suffix}>OF {standings.length}</span>
            </div>
            <div className={`${styles.trend} ${us.rank <= playoffLine ? styles.trendUp : styles.trendDown}`}>
              <span className={styles.arrow}>{us.rank <= playoffLine ? '^' : 'v'}</span>
              {isOffseason
                ? `FINAL · SEASON CONCLUDED`
                : playoffsActive
                  ? `REG. SEASON FINAL · #${us.rank} SEED`
                  : us.rank <= playoffLine
                    ? 'IN PLAYOFF POSITION'
                    : 'OUTSIDE PLAYOFF LINE'}
            </div>
          </div>

          <div className={styles.glanceCell}>
            <span className={styles.lbl}>Season Record</span>
            <div className={styles.recordRow}>
              <span className={styles.rec}>{us.wins}-{us.losses}-{us.draws}</span>
              <span className={`${styles.diff} ${diffOf(us) < 0 ? styles.diffNeg : ''}`.trim()}>
                {formatDiff(diffOf(us))}
              </span>
            </div>
            <FormStub label={us.latest_approach} />
          </div>

          <div className={styles.glanceCell}>
            <span className={styles.lbl}>Playoff Race</span>
            <div className={styles.race}>
              {standings.slice(0, Math.min(standings.length, playoffLine + 1)).map((standing) => (
                <span
                  key={standing.rank}
                  className={`${styles.racePip} ${standing.rank <= playoffLine ? styles.racePipIn : styles.racePipOut} ${standing.is_user_club ? styles.racePipUs : ''}`.trim()}
                >
                  <span className={styles.rk}>{standing.rank}</span>
                </span>
              ))}
            </div>
            <div className={styles.cushion}>
              <span className={styles.cushionPos}>{raceSummary.left}</span>
              <span className={styles.cushionSep}>-</span>
              <span className={styles.cushionBack}>{raceSummary.right}</span>
            </div>
          </div>

          <div className={styles.glanceCell}>
            <span className={styles.lbl}>This Week's Target</span>
            <NeedState action={needCopy.action} outcome={needCopy.outcome} helper={needCopy.helper} />
          </div>
        </div>

        <div className={styles.tableCard}>
          <div className={styles.tableHead}>
            <div>
              <span className={styles.kicker}>{data.division ? data.division.name : 'League Office'}</span>
              <h2 className={styles.tableTitle}>
                {playoffsActive ? 'Final Regular-Season Table' : 'Season Standings'}
                {playoffsActive && <>{' '}<span className={styles.subtle}>Playoffs live above</span></>}
              </h2>
              {data.division?.movement?.summary && (
                <span className={styles.subtle} style={{ display: 'block' }}>{data.division.movement.summary}</span>
              )}
            </div>
            <div className={styles.tableMeta}>
              {data.division && (
                <Tag tone="neutral">{data.division.short_name}</Tag>
              )}
              <Tag tone="live">WEEK {String(data.current_week).padStart(2, '0')}</Tag>
              <Tag tone="verified">TOP {playoffLine}</Tag>
              <Tag tone="neutral">{standings.length} CLUBS</Tag>
            </div>
          </div>

          <div className={styles.tableScroll}>
            <table className={styles.table}>
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
                        <tr className={styles.cutLine}>
                          <td colSpan={8}>
                            <div className={styles.cutRow}>
                              <span className={styles.cutBar} />
                              <span className={styles.cutLabel}>Playoff Cut</span>
                              <span className={styles.cutBar} />
                            </div>
                          </td>
                        </tr>
                      )}
                      <tr
                        className={standing.is_user_club ? styles.userRow : ''}
                        onClick={() => handleClubModal(standing.club_id, standing.club_name)}
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
                          <span className={`${styles.rank} ${standing.rank <= playoffLine ? styles.rankIn : styles.rankOut}`}>{standing.rank}</span>
                        </td>
                        <td>
                          <div className={styles.club}>
                            <Truncate className={styles.clubName}>{standing.club_name}</Truncate>
                            <div className={styles.clubArchetype}>
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
                        <td className="num"><span className={styles.cellNum}>{standing.wins}</span></td>
                        <td className="num"><span className={`${styles.cellNum} ${styles.cellNumMuted}`}>{standing.losses}</span></td>
                        <td className="num"><span className={`${styles.cellNum} ${styles.cellNumMuted}`}>{standing.draws}</span></td>
                        <td className="num"><span className={`${styles.cellNum} ${styles.cellNumPts}`}>{standing.points}</span></td>
                        <td>
                          <Tag tone={approachTone(standing.latest_approach)}>
                            {normalizeApproach(standing.latest_approach)}
                          </Tag>
                        </td>
                        <td><DiffBar diff={diffOf(standing)} max={maxDiff} /></td>
                      </tr>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className={styles.tableFoot}>
            <span className={styles.legendItem}><Tag tone="live">YOU</Tag> User club row</span>
            <span className={styles.legendSep}>-</span>
            <span className={styles.legendItem}><Tag tone="out">CUT</Tag> Playoff line</span>
            <span className={styles.legendSep}>-</span>
            <span className={styles.legendItem}>
              <TermTip term="standings.playoff_line">Playoff Line</TermTip>
              {' '}— top {playoffLine} advance
            </span>
            <span className={styles.legendSep}>-</span>
            <span className={styles.legendNote}>Click any row to open that club's program history.</span>
          </div>
        </div>

        <div className={styles.side}>
          <div className={styles.panel}>
            <div className={styles.panelHead}>
              <span className={styles.kicker}>League Wire</span>
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
                className={styles.wireTicker}
                role="list"
                aria-label="Recent league results"
              >
                {wireRows}
              </div>
            )}
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHead}>
              <span className={styles.kicker}>Tiebreaker Read</span>
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
              <div className={styles.tbList}>
                {tiebreakRows.map((standing) => {
                  const isSafe = standing.rank <= playoffLine;
                  return (
                    <div
                      key={`tb-${standing.club_id}`}
                      className={styles.tbRow}
                      onClick={() => handleClubModal(standing.club_id, standing.club_name)}
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
                      <span className={styles.tbFrom}>#{standing.rank}</span>
                      <div className={styles.tbBody}>
                        <Truncate className={styles.tbWho}>{standing.club_name}</Truncate>
                        <span className={styles.tbNote}>
                          {standing.points} pts · {formatDiff(diffOf(standing))} diff
                        </span>
                      </div>
                      <span className={`${styles.tbRisk} ${isSafe ? styles.tbRiskLow : styles.tbRiskHigh}`}>
                        {isSafe ? 'IN' : 'BUBBLE'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {data.divisions && data.divisions.length > 1 && (
            <PyramidPanel
              divisions={data.divisions}
              isOfficial={isOfficial}
              onClubClick={handleClubModal}
            />
          )}
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

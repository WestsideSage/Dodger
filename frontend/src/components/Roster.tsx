import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { Player, RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { rosterApi } from '../api/client';
import { StatusMessage, Table, StatBar, CeilingBadge } from '../ui';
import type { CeilingGradeLetter } from '../ui';
import { PlayerDetailModal } from './PlayerDetailModal';
import { LineupEditor } from './lineup/LineupEditor';
import { Sparkline } from './roster/Sparkline';
import { TermTip } from '../legibility';
import type { TermId } from '../legibility';
import { potentialRank } from '../domain/tiers';
import styles from './Roster.module.css';

// Maps player.role strings to their TermId. Exhaustive over all 8 archetypes
// that archetype_for_player() can emit (see recruitment._RECRUITMENT_DISPLAY_NAMES).
const ROLE_TERM_ID: Record<string, TermId> = {
  'Sharpshooter':         'archetype.sharpshooter',
  'Net Specialist':       'archetype.net_specialist',
  'Ball Hawk':            'archetype.ball_hawk',
  'Iron Anchor':          'archetype.iron_anchor',
  'Two-Way Threat':       'archetype.two_way_threat',
  'Skirmisher':           'archetype.skirmisher',
  'Possession Specialist':'archetype.possession_specialist',
  'Hit-and-Run':          'archetype.hit_and_run',
};

type RosterEntry = {
  player: Player;
  starter: boolean;
};

const archetypeBadge = (label: string) => (
  <span className={styles.roleBadge}>{label.toUpperCase()}</span>
);

/** §3.5 ceiling ladder: derive the gold letter grade from a numeric ceiling.
 *  Returns null when no ceiling is known, so no badge is rendered. */
function ceilingGradeFromCeiling(ceiling: number | null | undefined): CeilingGradeLetter | null {
  if (ceiling == null) return null;
  if (ceiling >= 92) return 'A+';
  if (ceiling >= 88) return 'A';
  if (ceiling >= 84) return 'A-';
  if (ceiling >= 80) return 'B+';
  if (ceiling >= 76) return 'B';
  if (ceiling >= 72) return 'B-';
  return 'C';
}

const potentialGlyph = (tier: string) => {
  if (tier === 'Elite') return '★';
  if (tier === 'High') return '◆';
  if (tier === 'Mid') return '»';
  if (tier === 'Low') return '⬡';
  return '⚬';
};

function roleBucket(label: string): 'Power' | 'Balanced' | 'Tactical' {
  const normalized = label.toLowerCase();
  if (normalized.includes('sharpshooter') || normalized.includes('skirmisher')) return 'Power';
  if (
    normalized.includes('net specialist')
    || normalized.includes('possession specialist')
    || normalized.includes('hit-and-run')
  ) {
    return 'Tactical';
  }
  return 'Balanced';
}

function styleBucket(player: Player): 'Power' | 'Balanced' | 'Tactical' {
  const powerSignal = player.ratings.accuracy + player.ratings.power;
  const tacticalSignal = player.ratings.catch + player.ratings.tactical_iq;
  const balancedSignal = player.ratings.dodge + player.ratings.stamina;
  const maxSignal = Math.max(powerSignal, tacticalSignal, balancedSignal);
  if (maxSignal === powerSignal) return 'Power';
  if (maxSignal === tacticalSignal) return 'Tactical';
  return roleBucket(player.role);
}

// Mix segment colors are token-driven custom properties supplied at the call
// site (a CSS variable assignment, not a literal in the module CSS).
const segVar = (token: string): CSSProperties => ({ '--seg': `var(${token})` } as CSSProperties);

const LineupSummary = ({ roster }: { roster: RosterEntry[] }) => {
  const starters = roster.filter(entry => entry.starter).length;
  const reservePool = Math.max(0, roster.length - starters);
  const rotation = Math.min(2, reservePool);
  const bench = Math.max(0, reservePool - rotation);
  const avgOvr = roster.length > 0
    ? Math.round(roster.reduce((total, entry) => total + entry.player.overall, 0) / roster.length)
    : 0;

  return (
    <div className={styles.glanceCell}>
      <span className={styles.kicker}>Lineup · OVR {avgOvr}</span>
      <div className={styles.lineRow}>
        <span className={styles.linePill}><span>{starters}</span> STARTERS</span>
        <span className={styles.linePill}><span>{rotation}</span> ROTATION</span>
        <span className={styles.linePill}><span>{bench}</span> BENCH</span>
      </div>
      <p className={styles.lineHelper}>
        {bench + rotation === 0
          ? 'Roster is bare — recruit or sign reserves before fatigue catches you.'
          : 'Starting core is set. Balance the rotation and manage fatigue.'}
      </p>
    </div>
  );
};

const ArchetypeMix = ({ roster }: { roster: RosterEntry[] }) => {
  const counts = roster.reduce<Record<'Power' | 'Balanced' | 'Tactical', number>>(
    (acc, entry) => {
      acc[styleBucket(entry.player)] += 1;
      return acc;
    },
    { Power: 0, Balanced: 0, Tactical: 0 },
  );

  const segments = [
    { key: 'Power', value: counts.Power, token: '--volt' },
    { key: 'Balanced', value: counts.Balanced, token: '--ok' },
    { key: 'Tactical', value: counts.Tactical, token: '--gold' },
  ];

  return (
    <div className={styles.glanceCell}>
      <span className={styles.kicker}>Archetype Mix</span>
      <div className={styles.mixBar}>
        {segments.map((segment) => (
          <div
            key={segment.key}
            className={styles.mixSeg}
            style={{ flex: Math.max(segment.value, 1), ...segVar(segment.token) }}
          />
        ))}
      </div>
      <div className={styles.mixLegend}>
        {segments.map((segment) => (
          <div key={segment.key} className={styles.mixItem}>
            <span className={styles.mixDot} style={segVar(segment.token)} />
            <span>{segment.key}</span>
            <span className={styles.mixVal}>{segment.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const PotentialBlock = ({ roster }: { roster: RosterEntry[] }) => {
  const tiers = ['Elite', 'High', 'Mid', 'Low', 'Raw'];
  const pipClass = (tier: string) =>
    tier === 'Elite' ? styles.potPipElite : tier === 'High' ? styles.potPipHigh : '';
  return (
    <div className={styles.glanceCell}>
      <span className={styles.kicker}>Potential Tiers</span>
      <div className={styles.potRow}>
        {tiers.map((tier) => (
          <div key={tier} className={`${styles.potPip} ${pipClass(tier)}`.trim()}>
            <span className="glyph">{potentialGlyph(tier)}</span>
            <span className="num">{roster.filter((entry) => entry.player.potential_tier === tier).length}</span>
            <span className="name">{tier}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const AgeCurve = ({ roster }: { roster: RosterEntry[] }) => {
  const ages = roster.map((entry) => entry.player.age);
  const min = ages.length > 0 ? Math.min(...ages) : 0;
  const max = ages.length > 0 ? Math.max(...ages) : 0;
  const avg = ages.length > 0 ? Math.round(ages.reduce((total, age) => total + age, 0) / ages.length) : 0;
  const buckets = [
    { label: '18-21', min: 18, max: 21 },
    { label: '22-25', min: 22, max: 25 },
    { label: '26-29', min: 26, max: 29 },
    { label: '30+', min: 30, max: 99 },
  ];
  const counts = buckets.map((bucket) => roster.filter((entry) => entry.player.age >= bucket.min && entry.player.age <= bucket.max).length);
  const maxCount = Math.max(...counts, 1);

  return (
    <div className={styles.glanceCell}>
      <span className={styles.kicker}>Age Curve</span>
      <div className={styles.ageRow}>
        <div className={styles.ageStat}>
          <span className="big">{avg}</span>
          <span className="dim">avg · {min}-{max}</span>
        </div>
        <div className={styles.ageBars}>
          {buckets.map((bucket, index) => (
            <div key={bucket.label} className={styles.ageCol}>
              <div className="bar" style={{ height: `${(counts[index] / maxCount) * 100}%` }} />
              <span className="lblMini">{bucket.label}</span>
              <span className="ct">{counts[index]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const RATING_TOOLTIPS: Record<string, string> = {
  ACC: 'Accuracy — how often throws hit their target.',
  POW: 'Power — throw speed and difficulty to dodge or catch.',
  DOD: 'Dodge — ability to evade incoming throws.',
  CAT: 'Catch — ability to snag incoming throws cleanly.',
  STA: 'Stamina — staying power across a long match.',
  IQ: 'IQ — court awareness, timing, and play reading.',
};

export function Roster() {
  const { data, loading, error, setData } = useApiResource<RosterResponse>('/api/roster');
  const [view, setView] = useState<'detailed' | 'compact'>('detailed');
  const [sortKey, setSortKey] = useState<'lineup' | 'potential' | 'overall' | 'age'>('lineup');
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [lineupEditorOpen, setLineupEditorOpen] = useState(false);

  const defaultLineupIds = useMemo(
    () => new Set((data?.default_lineup ?? []).slice(0, 6)),
    [data?.default_lineup],
  );

  const roster = useMemo(() => {
    const entries = (data?.roster ?? []).map((player) => ({
      player,
      starter: defaultLineupIds.has(player.id),
    }));

    if (sortKey === 'lineup') {
      entries.sort((left, right) => Number(right.starter) - Number(left.starter) || right.player.overall - left.player.overall);
    } else if (sortKey === 'potential') {
      entries.sort(
        (left, right) =>
          potentialRank(left.player.potential_tier) - potentialRank(right.player.potential_tier)
          || right.player.overall - left.player.overall,
      );
    } else if (sortKey === 'overall') {
      entries.sort((left, right) => right.player.overall - left.player.overall);
    } else {
      entries.sort((left, right) => left.player.age - right.player.age);
    }

    return entries;
  }, [data?.roster, defaultLineupIds, sortKey]);

  if (loading) return <StatusMessage title="Loading roster">Building the club sheet.</StatusMessage>;
  if (error) return <StatusMessage title="Roster unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No roster">No roster data returned.</StatusMessage>;

  const sortIndicators: Record<string, { label: string; dir: string }> = {
    lineup:    { label: 'Lineup',    dir: '→ OVR ↓' },
    potential: { label: 'Potential', dir: 'Elite first' },
    overall:   { label: 'OVR',       dir: '↓ highest' },
    age:       { label: 'Age',       dir: '↑ youngest' },
  };
  const ind = sortIndicators[sortKey];

  return (
    <div className={`max-content ${styles.shell}`} data-screen-label="02 Roster">
      <div className={styles.head}>
        <div>
          <h2 className={styles.title}>Team Roster</h2>
          <p className={styles.sub}>Player condition, role fit, and match readiness. {data.roster.length} contracted.</p>
        </div>
        <div className={styles.headActions}>
          <div className={styles.segment}>
            <button className={`${styles.segBtn} ${view === 'detailed' ? styles.segBtnActive : ''}`} onClick={() => setView('detailed')}>Detailed</button>
            <button className={`${styles.segBtn} ${view === 'compact' ? styles.segBtnActive : ''}`} onClick={() => setView('compact')}>Compact</button>
          </div>
          <select data-testid="roster-sort" className={styles.sort} value={sortKey} onChange={(event) => setSortKey(event.target.value as typeof sortKey)}>
            <option value="lineup">Lineup order (starters first, then OVR ↓)</option>
            <option value="potential">Potential tier (Elite → Low)</option>
            <option value="overall">OVR highest first ↓</option>
            <option value="age">Age youngest first ↑</option>
          </select>
          <span aria-label={`Sorted by ${ind.label}, ${ind.dir}`} className={styles.sortIndicator}>
            {ind.label} {ind.dir}
          </span>
          <button
            className={styles.editorBtn}
            type="button"
            onClick={() => setLineupEditorOpen(true)}
          >
            Lineup Editor ▸
          </button>
        </div>
      </div>

      <div className={styles.glance}>
        <LineupSummary roster={roster} />
        <ArchetypeMix roster={roster} />
        <PotentialBlock roster={roster} />
        <AgeCurve roster={roster} />
      </div>

      <div className={styles.tableCard}>
        <Table
          density={view === 'detailed' ? 'comfortable' : 'compact'}
          data-testid="roster-table"
          className={styles.rosterTable}
        >
          <thead>
            {view === 'compact' ? (
              <tr>
                <th className="num">#</th>
                <th>Player</th>
                <th className="num" title="Accuracy — how often throws hit their target.">ACC</th>
                <th className="num" title="Power — throw speed and difficulty to dodge or catch.">POW</th>
                <th className="num" title="Dodge — ability to evade incoming throws.">DOD</th>
                <th className="num" title="Catch — ability to snag incoming throws cleanly.">CAT</th>
                <th className="num" title="Stamina — staying power across a long match.">STA</th>
                <th className="num" title="IQ — court awareness, timing, and play reading.">IQ</th>
                <th className="num" title="Overall — weighted blend of every rating.">OVR</th>
                <th>Potential</th>
                <th>Role</th>
              </tr>
            ) : (
              <tr>
                <th className="num">#</th>
                <th>Player</th>
                <th>Ratings</th>
                <th>Potential</th>
                <th>OVR</th>
                <th>Role</th>
              </tr>
            )}
          </thead>
          <tbody>
            {roster.map(({ player, starter }, index) => {
              const isElite = player.potential_tier === 'Elite';
              const ceilingGrade = ceilingGradeFromCeiling(player.potential_ceiling);
              const tierClass =
                player.potential_tier === 'Elite' ? styles.potTierElite
                : player.potential_tier === 'High' ? styles.potTierHigh : '';
              return (
                <tr
                  key={player.id}
                  data-testid="roster-row"
                  className={`${isElite ? styles.rowElite : ''} ${starter ? styles.rowStarter : ''}`.trim()}
                  style={{ cursor: 'pointer' }}
                  // WT-21: keep the row a PLAIN table row so the per-column
                  // rating <td>s stay in the accessibility tree and the
                  // role-cell TermTip <button> is not nested inside an
                  // interactive role. Mouse users can click anywhere on the
                  // row; the keyboard/SR activator is the player-name <button>.
                  onClick={() => setSelectedPlayer(player)}
                >
                  <td className={`num ${styles.rank}`}>{String(index + 1).padStart(2, '0')}</td>
                  <td>
                    <div className={styles.player}>
                      <button
                        type="button"
                        className={styles.playerNameBtn}
                        aria-label={`${player.name}, OVR ${player.overall}, ${player.role} — open player card`}
                        onClick={(e) => { e.stopPropagation(); setSelectedPlayer(player); }}
                      >
                        <span data-testid="roster-row-name" className={styles.playerName}>{player.name}</span>
                      </button>
                      <div className={styles.playerMeta}>
                        <span>Age {player.age}</span>
                        {starter && <span data-testid="roster-row-starter-pin" className={styles.pin}>●</span>}
                      </div>
                    </div>
                  </td>
                  {view === 'compact' ? (
                    ([
                      ['ACC', player.ratings.accuracy],
                      ['POW', player.ratings.power],
                      ['DOD', player.ratings.dodge],
                      ['CAT', player.ratings.catch],
                      ['STA', player.ratings.stamina],
                      ['IQ', player.ratings.tactical_iq],
                    ] as Array<[string, number]>).map(([label, value]) => {
                      const numericValue = Number(value);
                      const tierClassName =
                        numericValue >= 85 ? styles.tierElite
                        : numericValue >= 70 ? styles.tierGood
                        : numericValue >= 55 ? styles.tierAvg : styles.tierPoor;
                      return <td key={label} className={`num ${styles.numCell} ${tierClassName}`}>{Math.round(numericValue)}</td>;
                    })
                  ) : (
                    <td>
                      <div className={styles.ratings}>
                        {([
                          ['ACC', player.ratings.accuracy],
                          ['POW', player.ratings.power],
                          ['DOD', player.ratings.dodge],
                          ['CAT', player.ratings.catch],
                          ['STA', player.ratings.stamina],
                          ['IQ', player.ratings.tactical_iq],
                        ] as Array<[string, number]>).map(([label, value]) => (
                          <StatBar key={label} label={label} value={Number(value)} title={RATING_TOOLTIPS[label] ?? label} />
                        ))}
                      </div>
                    </td>
                  )}
                  <td>
                    <div className={styles.potential}>
                      {ceilingGrade && <CeilingBadge grade={ceilingGrade} aria-label={`Ceiling grade ${ceilingGrade}`} />}
                      <div className={styles.potInfo}>
                        <span className={`${styles.potTier} ${tierClass}`.trim()}>{player.potential_tier}</span>
                        <span className={styles.potConf}>{'●'.repeat(player.scouting_confidence)}{'○'.repeat(Math.max(0, 4 - player.scouting_confidence))}</span>
                      </div>
                    </div>
                  </td>
                  {view === 'compact' ? (
                    <td className={`num ${styles.numCell}`}>{player.overall}</td>
                  ) : (
                    <td>
                      <div className={styles.ovr}>
                        <span className={styles.ovrVal}>{player.overall}</span>
                        {player.ovr_season_trend != null && player.ovr_season_trend.length >= 2 ? (
                          <Sparkline data={player.ovr_season_trend} />
                        ) : (
                          <div
                            data-testid="roster-ovr-nodata"
                            title="Last-offseason OVR change shown here after first offseason completes"
                            className={styles.ovrSpark}
                          >
                            <div className={styles.ovrFill} style={{ width: `${player.overall}%` }} />
                          </div>
                        )}
                      </div>
                    </td>
                  )}
                  <td
                    onClick={(e) => e.stopPropagation()}
                    style={{ cursor: 'default' }}
                  >
                    {ROLE_TERM_ID[player.role]
                      ? (
                        <TermTip term={ROLE_TERM_ID[player.role] as TermId}>
                          {archetypeBadge(player.role)}
                        </TermTip>
                      )
                      : archetypeBadge(player.role)
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
        <div className={styles.foot}>
          <span className={styles.footItem}><span className="gem">{potentialGlyph('Elite')}</span> Elite ceiling</span>
          <span className={styles.footSep}>·</span>
          <span className={styles.footItem}><span className="gem">{potentialGlyph('High')}</span> Strong projection</span>
          <span className={styles.footSep}>·</span>
          <span className={styles.footItem}><span className="gem">{potentialGlyph('Mid')}</span> Rotation upside</span>
          <span className={styles.footNote}>Live roster data sorted from the active club sheet.</span>
        </div>
      </div>

      {selectedPlayer && (
        <PlayerDetailModal
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
          // Playtest 3 F-8: the release control lives on the player card —
          // the journal searched every screen for a cut/waive action and
          // found none. Blocked (not hidden) at the 6-player floor so the
          // rule is visible.
          releaseBlockedReason={
            data.roster.length <= 6
              ? 'Roster is at the 6-player floor — sign someone before releasing.'
              : null
          }
          hasOpenPromise={(data.open_promise_player_ids ?? []).includes(selectedPlayer.id)}
          onRelease={() =>
            rosterApi.release(selectedPlayer.id).then((body) => {
              setData((prev) =>
                prev
                  ? {
                      ...prev,
                      roster: body.roster,
                      default_lineup: body.default_lineup,
                      open_promise_player_ids: body.open_promise_player_ids,
                    }
                  : prev,
              );
              setSelectedPlayer(null);
            })
          }
        />
      )}
      {lineupEditorOpen && data && (
        <LineupEditor
          roster={data.roster}
          defaultLineup={data.default_lineup}
          autoReorder={data.lineup_auto_reorder ?? true}
          onClose={() => setLineupEditorOpen(false)}
          onSaved={(orderedPlayerIds) => {
            // Splice the server-returned order into the cached roster payload so
            // the Roster screen reflects the resolved starting six immediately —
            // both for manual saves and Auto-Assign. Functional update: a manual
            // save fires onAutoReorderChange in the same tick, so a captured
            // `data` would clobber its field.
            setData((prev) => (prev ? { ...prev, default_lineup: orderedPlayerIds } : prev));
          }}
          onAutoReorderChange={(enabled) =>
            setData((prev) => (prev ? { ...prev, lineup_auto_reorder: enabled } : prev))
          }
        />
      )}
    </div>
  );
}

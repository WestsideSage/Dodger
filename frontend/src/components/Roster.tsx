import { useMemo, useState } from 'react';
import type { Player, RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { StatusMessage } from './ui';
import { PlayerDetailModal } from './PlayerDetailModal';
import { LineupEditor } from './lineup/LineupEditor';

type RosterEntry = {
  player: Player;
  starter: boolean;
};

const archetypeBadge = (label: string) => {
  const tone = roleBucket(label);
  const badgeTone =
    tone === 'Power'
      ? 'dm-badge-orange'
      : tone === 'Tactical'
      ? 'dm-badge-violet'
      : 'dm-badge-cyan';
  return <span className={`dm-badge ${badgeTone}`}>{label.toUpperCase()}</span>;
};

const potentialColor = (tier: string) => {
  if (tier === 'Elite') return '#facc15';
  if (tier === 'High') return 'var(--dm-cyan)';
  if (tier === 'Solid') return '#84cc16';
  return '#94a3b8';
};

const potentialGlyph = (tier: string) => {
  if (tier === 'Elite') return '\u2605';
  if (tier === 'High') return '\u25C6';
  if (tier === 'Mid') return '\u00BB';
  if (tier === 'Low') return '\u2B21';
  return '\u26AC';
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

const LineupSummary = ({ roster }: { roster: RosterEntry[] }) => {
  const starters = roster.filter(entry => entry.starter).length;
  const reservePool = Math.max(0, roster.length - starters);
  const rotation = Math.min(2, reservePool);
  const bench = Math.max(0, reservePool - rotation);
  const avgOvr = roster.length > 0
    ? Math.round(roster.reduce((total, entry) => total + entry.player.overall, 0) / roster.length)
    : 0;

  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Lineup · OVR {avgOvr}</span>
      <div className="rl-line-row">
        <span className="rl-line-pill starter"><span>{starters}</span> STARTERS</span>
        <span className="rl-line-pill rotation"><span>{rotation}</span> ROTATION</span>
        <span className="rl-line-pill bench"><span>{bench}</span> BENCH</span>
      </div>
      <p className="rl-line-helper">
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
    { key: 'Power', value: counts.Power, color: 'var(--dm-orange)' },
    { key: 'Balanced', value: counts.Balanced, color: 'var(--dm-cyan)' },
    { key: 'Tactical', value: counts.Tactical, color: 'var(--dm-violet)' },
  ];

  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Archetype Mix</span>
      <div className="rl-mix-bar">
        {segments.map((segment) => (
          <div
            key={segment.key}
            className="seg"
            style={{ flex: Math.max(segment.value, 1), background: segment.color }}
          />
        ))}
      </div>
      <div className="rl-mix-legend">
        {segments.map((segment) => (
          <div key={segment.key} className="item">
            <span className="dot" style={{ background: segment.color }} />
            <span className="k">{segment.key}</span>
            <span className="v mono">{segment.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const PotentialBlock = ({ roster }: { roster: RosterEntry[] }) => {
  const tiers = ['Elite', 'High', 'Mid', 'Low', 'Raw'];
  return (
    <div className="rl-glance-cell">
      <span className="dm-kicker">Potential Tiers</span>
      <div className="rl-pot-row">
        {tiers.map((tier) => (
          <div key={tier} className={`rl-pot-pip tier-${tier.toLowerCase()}`}>
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
    <div className="rl-glance-cell">
      <span className="dm-kicker">Age Curve</span>
      <div className="rl-age-row">
        <div className="rl-age-stat">
          <span className="big mono">{avg}</span>
          <span className="dim">avg · {min}-{max}</span>
        </div>
        <div className="rl-age-bars">
          {buckets.map((bucket, index) => (
            <div key={bucket.label} className="rl-age-col">
              <div className="bar" style={{ height: `${(counts[index] / maxCount) * 100}%` }} />
              <span className="lbl-mini">{bucket.label}</span>
              <span className="ct mono">{counts[index]}</span>
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

const RatingMini = ({ label, value }: { label: string; value: number }) => {
  const tier = value >= 85 ? 'elite' : value >= 70 ? 'good' : value >= 55 ? 'avg' : 'poor';
  return (
    <div className={`rl-rmini tier-${tier}`} title={RATING_TOOLTIPS[label] ?? label}>
      <span className="rl-rmini-lbl">{label}</span>
      <span className="rl-rmini-val mono">{Math.round(value)}</span>
      <div className="rl-rmini-bar">
        <div className="fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
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
      const order: Record<string, number> = { Elite: 0, High: 1, Solid: 2, Limited: 3 };
      entries.sort(
        (left, right) =>
          (order[left.player.potential_tier] ?? 4) - (order[right.player.potential_tier] ?? 4)
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

  return (
    <div className="max-content rl-shell" data-screen-label="02 Roster">
      <div className="rl-head">
        <div>
          <span className="dm-kicker">Roster Lab</span>
          <h2 className="rl-title">Team Roster</h2>
          <p className="rl-sub">Player condition, role fit, and match readiness. {data.roster.length} contracted.</p>
        </div>
        <div className="rl-head-actions">
          <div className="rl-segment">
            <button className={`rl-seg-btn ${view === 'detailed' ? 'is-active' : ''}`} onClick={() => setView('detailed')}>Detailed</button>
            <button className={`rl-seg-btn ${view === 'compact' ? 'is-active' : ''}`} onClick={() => setView('compact')}>Compact</button>
          </div>
          <select className="rl-sort" value={sortKey} onChange={(event) => setSortKey(event.target.value as typeof sortKey)}>
            <option value="lineup">Sort · Lineup → OVR</option>
            <option value="potential">Sort · Potential</option>
            <option value="overall">Sort · OVR</option>
            <option value="age">Sort · Age</option>
          </select>
          <button
            className="dm-btn"
            type="button"
            onClick={() => setLineupEditorOpen(true)}
          >
            Lineup Editor ▸
          </button>
        </div>
      </div>

      <div className="rl-glance">
        <LineupSummary roster={roster} />
        <ArchetypeMix roster={roster} />
        <PotentialBlock roster={roster} />
        <AgeCurve roster={roster} />
      </div>

      <div className="rl-table-card">
        <div className="rl-table-scroll">
          <table className={`rl-table ${view}`}>
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
                return (
                  <tr 
                    key={player.id} 
                    className={`${isElite ? 'rl-row-elite' : ''} ${starter ? 'rl-row-starter' : ''}`.trim()}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedPlayer(player)}
                  >
                    <td className="num rl-rank">{String(index + 1).padStart(2, '0')}</td>
                    <td>
                      <div className="rl-player">
                        <span className="rl-player-name">{player.name}</span>
                        <div className="rl-player-meta">
                          <span>Age {player.age}</span>
                          <span className="dot">·</span>
                          {archetypeBadge(player.role)}
                          {starter && <span className="rl-pin">●</span>}
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
                        const tier = numericValue >= 85 ? 'elite' : numericValue >= 70 ? 'good' : numericValue >= 55 ? 'avg' : 'poor';
                        return <td key={label} className={`num rl-num tier-${tier}`}>{Math.round(numericValue)}</td>;
                      })
                    ) : (
                      <td>
                        <div className="rl-ratings">
                          {([
                            ['ACC', player.ratings.accuracy],
                            ['POW', player.ratings.power],
                            ['DOD', player.ratings.dodge],
                            ['CAT', player.ratings.catch],
                            ['STA', player.ratings.stamina],
                            ['IQ', player.ratings.tactical_iq],
                          ] as Array<[string, number]>).map(([label, value]) => (
                            <RatingMini key={label} label={label} value={Number(value)} />
                          ))}
                        </div>
                      </td>
                    )}
                    <td>
                      <div className="rl-potential">
                        <span className={`rl-gem tier-${player.potential_tier.toLowerCase()}`}>{potentialGlyph(player.potential_tier)}</span>
                        <div className="rl-pot-info">
                          <span className="rl-pot-tier" style={{ color: potentialColor(player.potential_tier) }}>{player.potential_tier}</span>
                          <span className="rl-pot-conf">{'●'.repeat(player.scouting_confidence)}{'○'.repeat(Math.max(0, 4 - player.scouting_confidence))}</span>
                        </div>
                      </div>
                    </td>
                    {view === 'compact' ? (
                      <td className="num rl-num">{player.overall}</td>
                    ) : (
                      <td>
                        <div className="rl-ovr">
                          <span className="rl-ovr-val">{player.overall}</span>
                          <div className="rl-ovr-spark">
                            <div className="rl-ovr-fill" style={{ width: `${player.overall}%` }} />
                          </div>
                        </div>
                      </td>
                    )}
                    <td>{archetypeBadge(player.role)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="rl-table-foot">
          <span className="rl-foot-item"><span className="rl-gem tier-elite">{potentialGlyph('Elite')}</span> Elite ceiling</span>
          <span className="rl-foot-sep">·</span>
          <span className="rl-foot-item"><span className="rl-gem tier-high">{potentialGlyph('High')}</span> Strong projection</span>
          <span className="rl-foot-sep">·</span>
          <span className="rl-foot-item"><span className="rl-gem tier-solid">{potentialGlyph('Solid')}</span> Rotation upside</span>
          <span className="rl-foot-note">Live roster data sorted from the active club sheet.</span>
        </div>
      </div>
      
      {selectedPlayer && (
        <PlayerDetailModal player={selectedPlayer} onClose={() => setSelectedPlayer(null)} />
      )}
      {lineupEditorOpen && data && (
        <LineupEditor
          roster={data.roster}
          defaultLineup={data.default_lineup}
          onClose={() => setLineupEditorOpen(false)}
          onSaved={(orderedPlayerIds) => {
            // If the server returned a fresh order, splice it into the
            // cached roster payload so the Roster screen reflects the new
            // starting six immediately. An empty list means "we cleared
            // the override" — let the next mount re-fetch the resolved
            // order from /api/roster.
            if (orderedPlayerIds.length > 0) {
              setData({ ...data, default_lineup: orderedPlayerIds });
            }
          }}
        />
      )}
    </div>
  );
}

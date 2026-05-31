import { useState } from 'react';
import { useApiResource } from '../../../hooks/useApiResource';
import { StatusMessage } from '../../ui';
import { EmptyState, ProofChip, TermTip } from '../../../legibility';
import { AlumniLineage } from './AlumniLineage';
import { BannerShelf } from './BannerShelf';
import { formatSeasonLabel, formatTimelineLabel, humanizeHistoryToken } from './formatters';

interface HeroSeason {
  season_label: string;
  wins: number;
  losses: number;
  draws: number;
  avg_ovr?: number;
  championships?: number;
}

interface TimelineEvent {
  season: string;
  week: number | null;
  event_type: string;
  label: string;
  weight: string;
  holder_name?: string | null;
  proof_stat?: string | null;
}

interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

interface BannerEntry {
  type: string;
  season: string;
  label: string;
}

interface ProgramTrajectory {
  club_id: string;
  season_id: string;
  archetype: string;
  dominant_intent: string;
  record_w: number;
  record_l: number;
  record_d: number;
  top_dev_archetype: string;
  recruiting_class_strength: string;
}

interface ProgramData {
  club_id: string;
  hero: {
    season_1?: HeroSeason;
    current?: HeroSeason;
  };
  timeline: TimelineEvent[];
  alumni: AlumnusEntry[];
  banners: BannerEntry[];
  program_archetype?: string;
  program_trajectories?: ProgramTrajectory[];
}

type ProgramFilter = 'all' | 'titles' | 'awards' | 'records' | 'legacy';

type DisplayEntry = {
  bucket: Exclude<ProgramFilter, 'all'>;
  copy: string;
  id: string;
  kicker: string;
  tag: string;
  tick: string;
  title: string;
  tone: 'amber' | 'cyan' | 'emerald' | 'rose' | 'violet';
  typeLabel: string;
  holderName?: string | null;
  proofStat?: string | null;
};

const FILTERS: Array<{ id: ProgramFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'titles', label: 'Titles' },
  { id: 'awards', label: 'Awards' },
  { id: 'records', label: 'Records' },
  { id: 'legacy', label: 'Legacy' },
];

function badgeToneClass(tone: DisplayEntry['tone']) {
  switch (tone) {
    case 'amber':
      return 'dm-badge-amber';
    case 'emerald':
      return 'dm-badge-emerald';
    case 'rose':
      return 'dm-badge-rose';
    case 'violet':
      return 'dm-badge-violet';
    default:
      return 'dm-badge-cyan';
  }
}

function seasonTick(season: string, week: number | null) {
  if (week !== null) {
    return `W${String(week).padStart(2, '0')}`;
  }
  const match = season.match(/season_(\d+)/i);
  if (match) {
    return `S${match[1].padStart(2, '0')}`;
  }
  return 'ARC';
}



function buildEntry(event: TimelineEvent): DisplayEntry {
  const seasonLabel = formatSeasonLabel(event.season);
  const title = formatTimelineLabel(event.label);

  switch (event.event_type) {
    case 'championship':
      return {
        bucket: 'titles',
        copy: `${seasonLabel} ended with a title run for this program.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Champions',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'amber',
        typeLabel: 'Title',
      };
    case 'award':
      return {
        bucket: 'awards',
        copy: event.holder_name
          ? `${event.holder_name} won ${title} in ${seasonLabel}.`
          : `${title} was claimed by a player from this program in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Award',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'emerald',
        typeLabel: 'Award',
        holderName: event.holder_name,
        proofStat: event.proof_stat,
      };
    case 'record':
      return {
        bucket: 'records',
        copy: `${title} became a league mark for this program in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'League record',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'cyan',
        typeLabel: 'Record',
      };
    case 'hof':
      return {
        bucket: 'legacy',
        copy: `${title} entered the Hall of Fame in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: 'Hall of Fame',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'violet',
        typeLabel: 'Legacy',
      };
    default:
      return {
        bucket: 'legacy',
        copy:
          event.week !== null
            ? `Logged in ${seasonLabel}, Week ${String(event.week).padStart(2, '0')}.`
            : `Logged in ${seasonLabel}.`,
        id: `${event.season}-${event.event_type}-${event.label}`,
        kicker: seasonLabel,
        tag: event.week !== null ? `Week ${String(event.week).padStart(2, '0')}` : 'Program milestone',
        tick: seasonTick(event.season, event.week),
        title,
        tone: 'rose',
        typeLabel: 'Milestone',
      };
  }
}

function fallbackEntry(programArchetype: string | undefined): DisplayEntry {
  return {
    bucket: 'legacy',
    copy: 'This archive will log titles, records, Hall of Fame moments, alumni, and banners as the career unfolds.',
    id: 'history-baseline',
    kicker: 'Archive online',
    tag: humanizeHistoryToken(programArchetype ?? 'Balanced Rebuild'),
    tick: 'NOW',
    title: 'Program history is ready',
    tone: 'cyan',
    typeLabel: 'Archive',
  };
}

function HeroCard({ data, highlight, label }: { data: HeroSeason; highlight?: boolean; label: string }) {
  return (
    <div className={`do-hist-hero-card ${highlight ? 'is-current' : ''}`}>
      <span className="do-hist-hero-label">{label}</span>
      <span className="do-hist-hero-season">{formatSeasonLabel(data.season_label)}</span>
      <span className="do-hist-hero-record">
        {data.wins}-{data.losses}-{data.draws}
      </span>
      <div className="do-hist-hero-meta">
        {data.championships ? (
          <span>{data.championships} title{data.championships === 1 ? '' : 's'}</span>
        ) : null}
      </div>
    </div>
  );
}

export function MyProgramView({ clubId, isSelf = true }: { clubId: string; isSelf?: boolean }) {
  const { data, error, loading } = useApiResource<ProgramData>(`/api/history/my-program?club_id=${encodeURIComponent(clubId)}`);
  const [filter, setFilter] = useState<ProgramFilter>('all');
  const [shelfTab, setShelfTab] = useState<'banners' | 'alumni'>('banners');

  if (error) {
    return (
      <StatusMessage title="History unavailable" tone="danger">
        {error}
      </StatusMessage>
    );
  }
  if (loading) {
    return <StatusMessage title="Loading history">Building the program archive.</StatusMessage>;
  }
  if (!data) return null;

  const currentHero = data.hero.current ?? data.hero.season_1 ?? null;
  const firstHero = data.hero.season_1 ?? null;
  const latestTrajectory = data.program_trajectories && data.program_trajectories.length > 0
    ? data.program_trajectories[data.program_trajectories.length - 1]
    : null;
  const championshipCount = data.banners.filter((banner) => banner.type === 'championship').length;
  const entries = data.timeline.length > 0 ? data.timeline.map(buildEntry) : [fallbackEntry(data.program_archetype)];
  const visibleEntries = filter === 'all' ? entries : entries.filter((entry) => entry.bucket === filter);
  const identityLabel = humanizeHistoryToken(latestTrajectory?.archetype ?? data.program_archetype ?? 'Balanced Rebuild');

  return (
    <div className="do-tab-content">
      {/* Glance strip — de-jargoned copy */}
      <div className="do-hist-glance">
        <div className="cell">
          <span className="lbl">Season Range</span>
          <span className="val">
            {currentHero ? formatSeasonLabel(currentHero.season_label) : 'Season 1'}
          </span>
          <span className="trend">
            {entries.length === 1 && entries[0].id === 'history-baseline'
              ? 'Archive is live — no milestones logged yet'
              : `${entries.length} milestone${entries.length === 1 ? '' : 's'} logged`}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">All-Time Record</span>
          <span className="val">
            {currentHero ? `${currentHero.wins}-${currentHero.losses}-${currentHero.draws}` : '—'}
          </span>
          <span className="trend">
            {currentHero ? 'Across completed seasons' : 'First completed season will appear here'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">
            <TermTip term="identity.intent">Program Identity</TermTip>
          </span>
          <span className="val">{identityLabel}</span>
          <span className="trend">
            {latestTrajectory
              ? `Lean: ${humanizeHistoryToken(latestTrajectory.dominant_intent)} — shaped by your season tactics`
              : 'Set at club creation · evolves from your season-by-season choices'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Championship Banners</span>
          <span className="val">{championshipCount}</span>
          <span className={`trend ${championshipCount > 0 ? 'ok' : ''}`}>
            {championshipCount > 0
              ? `${championshipCount} title${championshipCount === 1 ? '' : 's'} in the archive`
              : 'First banner still ahead'}
          </span>
        </div>
        <div className="cell">
          <span className="lbl">Alumni</span>
          <span className="val">{data.alumni.length}</span>
          <span className="trend">
            {data.alumni.length > 0
              ? `${data.alumni.length} player${data.alumni.length === 1 ? '' : 's'} who shaped this program`
              : isSelf ? 'Your first alumni season is ahead' : 'No departed players yet'}
          </span>
        </div>
      </div>

      {/* Timeline filter + list */}
      <div className="do-hist-filters">
        <div className="filters">
          {FILTERS.map((item) => {
            const count =
              item.id === 'all'
                ? entries.length
                : entries.filter((entry) => entry.bucket === item.id).length;
            return (
              <button
                key={item.id}
                className={`do-board-filter ${filter === item.id ? 'is-active' : ''}`}
                onClick={() => setFilter(item.id)}
                type="button"
              >
                {item.label}
                <span className="n">{count}</span>
              </button>
            );
          })}
        </div>
        <span className="do-board-meta">
          {isSelf ? 'Program archive' : `${clubId.toUpperCase()} archive`}
        </span>
      </div>

      <div className="do-hist-timeline">
        <div className="rail" />
        {visibleEntries.length > 0 ? (
          visibleEntries.map((entry) => (
            <article key={entry.id} className={`do-hist-entry tone-${entry.tone}`}>
              <div className="do-hist-wk">
                <span className="wk-num">{entry.tick}</span>
                <span className="dot" />
              </div>
              <div className="do-hist-body">
                <header>
                  <span className={`dm-badge ${badgeToneClass(entry.tone)}`}>{entry.typeLabel}</span>
                  <span className="kicker">{entry.kicker}</span>
                  <span className="tag">{entry.tag}</span>
                </header>
                <h4 className="title">{entry.title}</h4>
                <p className="copy">{entry.copy}</p>
                {entry.proofStat && entry.holderName ? (
                  <ProofChip
                    label={entry.holderName}
                    source={entry.proofStat}
                  />
                ) : entry.proofStat ? (
                  <ProofChip
                    label="View proof"
                    source={entry.proofStat}
                  />
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <article className="do-hist-entry tone-cyan">
            <div className="do-hist-wk">
              <span className="wk-num">NONE</span>
              <span className="dot" />
            </div>
            <div className="do-hist-body">
              <header>
                <span className="dm-badge dm-badge-cyan">Filter</span>
                <span className="kicker">No matching entries</span>
                <span className="tag">Clear filter</span>
              </header>
              <h4 className="title">No archive items in this lane</h4>
              <p className="copy">Switch back to All to see the full program archive.</p>
            </div>
          </article>
        )}
      </div>

      {/* Program Arc — kept, Avg OVR removed from HeroCard */}
      <div className="do-hist-grid">
        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">Program Arc</span>
            <h3>How it started vs today</h3>
          </div>
          {firstHero || currentHero ? (
            <div className="do-hist-hero-grid">
              {firstHero ? <HeroCard data={firstHero} label="Opening season" /> : null}
              {currentHero ? <HeroCard data={currentHero} label="Current snapshot" highlight /> : null}
            </div>
          ) : (
            <EmptyState
              title="No completed season archived yet"
              body="Your first full season record will appear here after the offseason ceremony."
            />
          )}
        </section>

        {/* Trajectory Log section REMOVED. Its data (dominant_intent) is still
            used in the glance strip above. MilestoneTree.tsx is untouched —
            it is the deferred archive-tree spec's territory. */}

        {/* Banner Shelf + Alumni Lineage folded into tabs (interim).
            The future archive-tree spec will re-home these into the dynamic tree. */}
        <section className="dm-panel do-hist-card">
          <div className="do-hist-card-head">
            <span className="dm-kicker">
              {shelfTab === 'banners' ? 'Banner Shelf' : 'Alumni Lineage'}
            </span>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button
                type="button"
                className={`do-board-filter${shelfTab === 'banners' ? ' is-active' : ''}`}
                onClick={() => setShelfTab('banners')}
              >
                Banners
              </button>
              <button
                type="button"
                className={`do-board-filter${shelfTab === 'alumni' ? ' is-active' : ''}`}
                onClick={() => setShelfTab('alumni')}
              >
                Alumni
              </button>
            </div>
          </div>
          {shelfTab === 'banners' ? (
            <BannerShelf banners={data.banners} showNextPlaceholder={isSelf} />
          ) : (
            <AlumniLineage alumni={data.alumni} />
          )}
        </section>
      </div>
    </div>
  );
}

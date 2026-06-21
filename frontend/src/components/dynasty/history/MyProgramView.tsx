import { useState } from 'react';
import { useApiResource } from '../../../hooks/useApiResource';
import { StatusMessage } from '../../../ui';
import { EmptyState, ProofChip, TermTip } from '../../../legibility';
import { AlumniLineage } from './AlumniLineage';
import { BannerShelf } from './BannerShelf';
import { formatSeasonLabel, formatTimelineLabel, humanizeHistoryToken } from './formatters';
import styles from './MyProgramView.module.css';

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

interface AllTimeRecord {
  wins: number;
  losses: number;
  draws: number;
  seasons: number;
}

interface ProgramData {
  club_id: string;
  hero: {
    season_1?: HeroSeason;
    current?: HeroSeason;
    /** True career totals summed over every season row (incl. in-progress).
        hero.current is only the latest season's snapshot. */
    all_time?: AllTimeRecord;
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
  // Record Room: titles (amber) get the brick accent; every other type uses the
  // ink badge. The original per-tone palette is retired with the legacy classes.
  return tone === 'amber' ? `${styles.badge} ${styles.badgeBrick}` : styles.badge;
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
    <div className={`${styles.heroCard} ${highlight ? styles.heroCardCurrent : ''}`}>
      <span className={styles.heroLabel}>{label}</span>
      <span className={styles.heroSeason}>{formatSeasonLabel(data.season_label)}</span>
      <span className={styles.heroRecord}>
        {data.wins}-{data.losses}-{data.draws}
      </span>
      <div className={styles.heroMeta}>
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
  const allTime = data.hero.all_time ?? null;
  const firstHero = data.hero.season_1 ?? null;
  const latestTrajectory = data.program_trajectories && data.program_trajectories.length > 0
    ? data.program_trajectories[data.program_trajectories.length - 1]
    : null;
  const championshipCount = data.banners.filter((banner) => banner.type === 'championship').length;
  const entries = data.timeline.length > 0 ? data.timeline.map(buildEntry) : [fallbackEntry(data.program_archetype)];
  const visibleEntries = filter === 'all' ? entries : entries.filter((entry) => entry.bucket === filter);
  const identityLabel = humanizeHistoryToken(latestTrajectory?.archetype ?? data.program_archetype ?? 'Balanced Rebuild');

  return (
    <div className={styles.content}>
      {/* Glance strip — de-jargoned copy */}
      <div className={styles.glance}>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Season Range</span>
          <span className={styles.cellVal}>
            {currentHero ? formatSeasonLabel(currentHero.season_label) : 'Season 1'}
          </span>
          <span className={styles.cellTrend}>
            {entries.length === 1 && entries[0].id === 'history-baseline'
              ? 'Archive is live — no milestones logged yet'
              : `${entries.length} milestone${entries.length === 1 ? '' : 's'} logged`}
          </span>
        </div>
        <div className={styles.cell}>
          {/* hero.current is the LATEST season's snapshot — rendering it under
              an "Across completed seasons" label showed a week-2 "1-0-0" as
              the program's all-time record. Use the real career totals; if an
              older payload lacks them, label the snapshot as what it is. */}
          <span className={styles.cellLbl}>{allTime ? 'All-Time Record' : 'Latest Season Record'}</span>
          <span className={styles.cellVal}>
            {allTime
              ? `${allTime.wins}-${allTime.losses}-${allTime.draws}`
              : currentHero
                ? `${currentHero.wins}-${currentHero.losses}-${currentHero.draws}`
                : '—'}
          </span>
          <span className={styles.cellTrend}>
            {allTime
              ? `Across ${allTime.seasons} completed season${allTime.seasons === 1 ? '' : 's'}`
              : currentHero
                ? formatSeasonLabel(currentHero.season_label)
                : 'First completed season will appear here'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>
            <TermTip term="identity.intent">Program Identity</TermTip>
          </span>
          <span className={styles.cellVal}>{identityLabel}</span>
          <span className={styles.cellTrend}>
            {latestTrajectory
              ? `Lean: ${humanizeHistoryToken(latestTrajectory.dominant_intent)} — shaped by your season tactics`
              : 'Set at club creation · evolves from your season-by-season choices'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Championship Banners</span>
          <span className={styles.cellVal}>{championshipCount}</span>
          <span className={`${styles.cellTrend} ${championshipCount > 0 ? styles.cellTrendOk : ''}`}>
            {championshipCount > 0
              ? `${championshipCount} title${championshipCount === 1 ? '' : 's'} in the archive`
              : 'First banner still ahead'}
          </span>
        </div>
        <div className={styles.cell}>
          <span className={styles.cellLbl}>Alumni</span>
          <span className={styles.cellVal}>{data.alumni.length}</span>
          <span className={styles.cellTrend}>
            {data.alumni.length > 0
              ? `${data.alumni.length} player${data.alumni.length === 1 ? '' : 's'} who shaped this program`
              : isSelf ? 'Your first alumni season is ahead' : 'No departed players yet'}
          </span>
        </div>
      </div>

      {/* Timeline filter + list */}
      <div className={styles.filters}>
        <div className={styles.filterRow}>
          {FILTERS.map((item) => {
            const count =
              item.id === 'all'
                ? entries.length
                : entries.filter((entry) => entry.bucket === item.id).length;
            return (
              <button
                key={item.id}
                className={`${styles.filter} ${filter === item.id ? styles.filterActive : ''}`}
                onClick={() => setFilter(item.id)}
                type="button"
              >
                {item.label}
                <span className={styles.filterCount}>{count}</span>
              </button>
            );
          })}
        </div>
        <span className={styles.meta}>
          {isSelf ? 'Program archive' : `${clubId.toUpperCase()} archive`}
        </span>
      </div>

      <div className={styles.timeline}>
        {visibleEntries.length > 0 ? (
          visibleEntries.map((entry) => (
            <article key={entry.id} className={styles.entry}>
              <div className={styles.wk}>
                <span className={styles.wkNum}>{entry.tick}</span>
              </div>
              <div className={styles.entryBody}>
                <header className={styles.entryHead}>
                  <span className={badgeToneClass(entry.tone)}>{entry.typeLabel}</span>
                  <span className={styles.kickerInline}>{entry.kicker}</span>
                  <span className={styles.tag}>{entry.tag}</span>
                </header>
                <h4 className={styles.entryTitle}>{entry.title}</h4>
                <p className={styles.entryCopy}>{entry.copy}</p>
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
          <article className={styles.entry}>
            <div className={styles.wk}>
              <span className={styles.wkNum}>NONE</span>
            </div>
            <div className={styles.entryBody}>
              <header className={styles.entryHead}>
                <span className={styles.badge}>Filter</span>
                <span className={styles.kickerInline}>No matching entries</span>
                <span className={styles.tag}>Clear filter</span>
              </header>
              <h4 className={styles.entryTitle}>No archive items in this lane</h4>
              <p className={styles.entryCopy}>Switch back to All to see the full program archive.</p>
            </div>
          </article>
        )}
      </div>

      {/* Program Arc — kept, Avg OVR removed from HeroCard */}
      <div className={styles.grid}>
        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>Program Arc</span>
            <h3 className={styles.cardTitle}>How it started vs today</h3>
          </div>
          {firstHero || currentHero ? (
            <div className={styles.heroGrid}>
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
        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardKicker}>
              {shelfTab === 'banners' ? 'Banner Shelf' : 'Alumni Lineage'}
            </span>
            <div className={styles.shelfTabs}>
              <button
                type="button"
                className={`${styles.filter}${shelfTab === 'banners' ? ` ${styles.filterActive}` : ''}`}
                onClick={() => setShelfTab('banners')}
              >
                Banners
              </button>
              <button
                type="button"
                className={`${styles.filter}${shelfTab === 'alumni' ? ` ${styles.filterActive}` : ''}`}
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

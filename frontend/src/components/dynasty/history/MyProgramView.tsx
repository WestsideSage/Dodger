import { useEffect, useState } from 'react';
import { MilestoneTree } from './MilestoneTree';
import { AlumniLineage } from './AlumniLineage';
import { BannerShelf } from './BannerShelf';

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

interface ProgramData {
  club_id: string;
  hero: { season_1?: HeroSeason; current?: HeroSeason };
  timeline: TimelineEvent[];
  alumni: AlumnusEntry[];
  banners: BannerEntry[];
}

function HeroCard({ data, label, highlight }: { data: HeroSeason; label: string; highlight: boolean }) {
  return (
    <div
      style={{
        flex: 1,
        border: `1px solid ${highlight ? '#10b981' : '#1e293b'}`,
        borderRadius: '8px',
        padding: '1rem',
        background: '#0a1628',
        boxShadow: highlight ? '0 0 12px #10b98133' : 'none',
      }}
    >
      <div style={{ fontSize: '0.6rem', color: highlight ? '#10b981' : '#475569', fontWeight: 700, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>{data.season_label}</div>
      <div style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.25rem' }}>
        {data.wins}–{data.losses}–{data.draws}
      </div>
      {data.avg_ovr !== undefined && (
        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg OVR {data.avg_ovr}</div>
      )}
      {data.championships !== undefined && data.championships > 0 && (
        <div style={{ fontSize: '0.75rem', color: '#f97316', marginTop: '0.25rem' }}>
          🏆 {data.championships} title{data.championships !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

export function MyProgramView({ clubId, isSelf = true }: { clubId: string; isSelf?: boolean }) {
  const [data, setData] = useState<ProgramData | null>(null);

  useEffect(() => {
    fetch(`/api/history/my-program?club_id=${clubId}`)
      .then((res) => res.json())
      .then(setData);
  }, [clubId]);

  if (!data) return <div style={{ color: '#475569', padding: '1rem' }}>Loading program history…</div>;

  const { hero, timeline, alumni, banners } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Hero Strip */}
      {(hero.season_1 || hero.current) && (
        <div className="dm-panel">
          <p className="dm-kicker">Program Arc</p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            {hero.season_1 && <HeroCard data={hero.season_1} label="How it started" highlight={false} />}
            {hero.current && <HeroCard data={hero.current} label="Today" highlight={true} />}
          </div>
        </div>
      )}

      {/* Milestone Tree */}
      <div className="dm-panel">
        <p className="dm-kicker">Program History</p>
        <div style={{ overflowX: 'auto' }}>
          <MilestoneTree timeline={timeline} />
        </div>
      </div>

      {/* Alumni + Banners */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div className="dm-panel" style={{ flex: 1, minWidth: '260px' }}>
          <p className="dm-kicker">Alumni Lineage</p>
          <AlumniLineage alumni={alumni} />
        </div>
        <div className="dm-panel" style={{ flex: 1, minWidth: '260px' }}>
          <p className="dm-kicker">Banner Shelf</p>
          <BannerShelf banners={banners} showNextPlaceholder={isSelf} />
        </div>
      </div>
    </div>
  );
}

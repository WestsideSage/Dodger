import { useEffect, useState } from 'react';
import { apiPost } from '../api/client';
import { useApiResource } from '../hooks/useApiResource';
import type { OffseasonBeat } from '../types';
import { StatusMessage } from './ui';
import { AwardsNight, Graduation, SigningDay, NewSeasonEve } from './ceremonies/Ceremonies';
import { ChampionReveal } from './ceremonies/ChampionReveal';
import { RecapStandings } from './ceremonies/RecapStandings';
import { DevelopmentResults } from './ceremonies/DevelopmentResults';
import { RookieClassPreview } from './ceremonies/RookieClassPreview';
import { RecordsRatified, HallOfFameInduction } from './ceremonies/StructuredOffseasonBeats';
import { RecruitmentChoice } from './ceremonies/RecruitmentChoice';

export function Offseason({ onBeatChange }: { onBeatChange?: (title: string | null) => void } = {}) {
  const { data: beat, error, loading, setData: setBeat, setError } = useApiResource<OffseasonBeat>('/api/offseason/beat');
  const [acting, setActing] = useState(false);

  useEffect(() => {
    onBeatChange?.(beat?.title ?? null);
  }, [beat?.title, onBeatChange]);

  // WT-12: route mutating offseason actions through apiPost so the per-process
  // launch token is attached (a raw fetch would be rejected with 403 once the
  // server enforces the token). apiPost throws ApiError(detail) on non-2xx,
  // which maps onto the existing error surface below.
  const act = (endpoint: string, body?: unknown) => {
    setActing(true);
    setError(null);
    apiPost<OffseasonBeat & { state?: { state?: string } }>(endpoint, body)
      .then(data => {
        if (data.state?.state === 'season_active_pre_match') {
          window.location.reload();
          return;
        }
        setBeat(data);
      })
      .catch(err => setError(err instanceof Error ? err.message : 'Action failed'))
      .finally(() => setActing(false));
  };

  if (loading && !beat) {
    return <StatusMessage title="Loading offseason">Preparing the ceremony.</StatusMessage>;
  }
  if (error && !beat) {
    return <StatusMessage title="Offseason unavailable" tone="danger">{error}</StatusMessage>;
  }
  if (!beat) return null;

  const advance = () => act('/api/offseason/advance');
  const recruit = (prospectId: string) => act('/api/offseason/recruit', { prospect_id: prospectId });
  const beginSeason = () => act('/api/offseason/begin-season');

  if (beat.key === 'champion') return <ChampionReveal beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'recap') return <RecapStandings beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'awards') return <AwardsNight beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'retirements') return <Graduation beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'development') return <DevelopmentResults beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'rookie_class_preview') return <RookieClassPreview beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'records_ratified') return <RecordsRatified beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'hof_induction') return <HallOfFameInduction beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'recruitment' && beat.can_recruit) return (
    <RecruitmentChoice beat={beat} onSign={recruit} acting={acting} />
  );
  if (beat.key === 'recruitment') return <SigningDay beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'schedule_reveal') return <NewSeasonEve beat={beat} onComplete={beginSeason} acting={acting} />;

  return (
    <StatusMessage title="Offseason beat unavailable" tone="danger">
      This ceremony step could not be displayed.
    </StatusMessage>
  );
}

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
  // Playtest 3 F-8: at a full roster the pick rides with the named release
  // (sign-over-cut); the release only commits when the contested pick lands.
  const recruit = (prospectId: string, releasePlayerId?: string) =>
    act('/api/offseason/recruit', {
      prospect_id: prospectId,
      ...(releasePlayerId ? { release_player_id: releasePlayerId } : {}),
    });
  const beginSeason = () => act('/api/offseason/begin-season');

  let content = (
    <StatusMessage title="Offseason beat unavailable" tone="danger">
      This ceremony step could not be displayed.
    </StatusMessage>
  );
  if (beat.key === 'champion') content = <ChampionReveal beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'recap') content = <RecapStandings beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'awards') content = <AwardsNight beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'retirements') content = <Graduation beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'development') content = <DevelopmentResults beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'rookie_class_preview') content = <RookieClassPreview beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'records_ratified') content = <RecordsRatified beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'hof_induction') content = <HallOfFameInduction beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'recruitment' && beat.can_recruit) content = (
    <RecruitmentChoice beat={beat} onSign={recruit} acting={acting} />
  );
  else if (beat.key === 'recruitment') content = <SigningDay beat={beat} onComplete={advance} acting={acting} />;
  else if (beat.key === 'schedule_reveal') content = <NewSeasonEve beat={beat} onComplete={beginSeason} acting={acting} />;

  // A rejected action (e.g. the roster-floor guard blocking a recruitment
  // skip) must be visible: the catch above stores the message, but the
  // beat-level early return only rendered errors when no beat was loaded.
  return (
    <>
      {error ? (
        <StatusMessage title="Action blocked" tone="danger">{error}</StatusMessage>
      ) : null}
      {content}
    </>
  );
}

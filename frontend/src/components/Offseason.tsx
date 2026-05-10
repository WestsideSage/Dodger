import { useState } from 'react';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { AwardsNight, Graduation, CoachingCarousel, SigningDay, NewSeasonEve } from './ceremonies/Ceremonies';

interface OffseasonBeat {
  beat_index: number;
  total_beats: number;
  key: string;
  title: string;
  body: string[];
  state: string;
  can_advance: boolean;
  can_recruit: boolean;
  can_begin_season: boolean;
  signed_player_id: string;
  signed_player?: { id: string; name: string; overall: number; age: number } | null;
}

export function Offseason() {
  const { data: beat, error, loading, setData: setBeat, setError } = useApiResource<OffseasonBeat>('/api/offseason/beat');
  const [acting, setActing] = useState(false);

  const act = (endpoint: string, method = 'POST') => {
    setActing(true);
    setError(null);
    fetch(endpoint, { method })
      .then(res => {
        if (!res.ok) return res.json().then(d => Promise.reject(new Error(d.detail || 'Action failed')));
        return res.json();
      })
      .then(data => {
        if (data.state?.state === 'season_active_pre_match') {
          window.location.reload();
          return;
        }
        setBeat(data);
      })
      .catch(err => setError(err.message))
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
  const recruit = () => act('/api/offseason/recruit');
  const beginSeason = () => act('/api/offseason/begin-season');

  if (beat.key === 'awards') return <AwardsNight beat={beat} onComplete={advance} />;
  if (beat.key === 'retirements') return <Graduation beat={beat} onComplete={advance} />;
  if (beat.key === 'staff_carousel') return <CoachingCarousel beat={beat} onComplete={advance} />;
  if (beat.key === 'recruitment' && beat.can_recruit) return (
     <div style={{ textAlign: 'center', padding: '4rem' }}>
       <h1 style={{ fontSize: '2rem', marginBottom: '2rem' }}>Signing Day</h1>
       <ActionButton variant="accent" onClick={recruit} disabled={acting}>
         {acting ? 'Signing...' : 'Sign Best Rookie'}
       </ActionButton>
     </div>
  );
  if (beat.key === 'recruitment') return <SigningDay beat={beat} onComplete={advance} />;
  if (beat.key === 'schedule_reveal') return <NewSeasonEve beat={beat} onComplete={beginSeason} />;

  // Fallback
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <PageHeader eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`} title={beat.title} />
      <div className="dm-panel">
        {beat.body.map((line: string, i: number) => <p key={i}>{line}</p>)}
        {beat.can_advance && <ActionButton onClick={advance}>Continue</ActionButton>}
        {beat.can_begin_season && <ActionButton onClick={beginSeason}>Start New Season</ActionButton>}
      </div>
    </div>
  );
}

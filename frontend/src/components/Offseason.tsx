import { useState } from 'react';
import { useApiResource } from '../hooks/useApiResource';
import type { OffseasonBeat } from '../types';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { AwardsNight, Graduation, SigningDay, NewSeasonEve } from './ceremonies/Ceremonies';

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

  if (beat.key === 'awards') return <AwardsNight beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'retirements') return <Graduation beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'recruitment' && beat.can_recruit) return (
    <section className="command-offseason-shell" data-testid="offseason-recruitment-action">
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title="Signing Day"
        description="Make the next roster move before the league finishes its commitments."
      />
      <div className="dm-panel command-offseason-feature">
        <p className="dm-kicker">Recruitment Desk</p>
        <h3>Best available rookie</h3>
        <p>
          Your staff has narrowed the class. Sign the strongest available prospect, then review the rest of the league's commitments.
        </p>
      </div>
      <div className="dm-panel command-action-bar">
        <div>
          <p className="dm-kicker">Next action</p>
          <p>Recruitment must be resolved before the offseason ceremony can continue.</p>
        </div>
        <div className="command-action-buttons">
          <ActionButton variant="primary" onClick={recruit} disabled={acting}>
            {acting ? 'Signing...' : 'Sign Best Rookie'}
          </ActionButton>
        </div>
      </div>
    </section>
  );
  if (beat.key === 'recruitment') return <SigningDay beat={beat} onComplete={advance} acting={acting} />;
  if (beat.key === 'schedule_reveal') return <NewSeasonEve beat={beat} onComplete={beginSeason} acting={acting} />;

  const bodyLines = typeof beat.body === 'string'
    ? beat.body.split('\n').map((line: string) => line.trim()).filter(Boolean)
    : [];

  return (
    <section className="command-offseason-shell" data-testid="offseason-beat">
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title={beat.title}
        description="Review the league update, then continue the offseason sequence."
        stats={
          <div className="command-offseason-progress" aria-label="Offseason beat progress">
            {Array.from({ length: beat.total_beats }).map((_, index) => (
              <span
                key={index}
                className={index <= beat.beat_index ? 'command-offseason-progress-step command-offseason-progress-step-active' : 'command-offseason-progress-step'}
              />
            ))}
          </div>
        }
      />

      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker">{beat.key.replaceAll('_', ' ')}</p>
        <h3>{beat.title}</h3>
        <div className="command-offseason-copy">
          {bodyLines.length === 0 ? (
            <p>No additional report details for this beat.</p>
          ) : (
            bodyLines.map((line: string, i: number) => <p key={`${line}-${i}`}>{line}</p>)
          )}
        </div>
      </article>

      {(beat.can_advance || beat.can_begin_season) && (
        <div className="dm-panel command-action-bar">
          <div>
            <p className="dm-kicker">Ceremony Control</p>
            <p>{beat.can_begin_season ? 'The offseason is complete. Start the next season when ready.' : 'Continue to the next offseason beat.'}</p>
          </div>
          <div className="command-action-buttons">
            {beat.can_advance && (
              <ActionButton variant="primary" onClick={advance} disabled={acting}>
                {acting ? 'Continuing...' : 'Continue'}
              </ActionButton>
            )}
            {beat.can_begin_season && (
              <ActionButton variant="primary" onClick={beginSeason} disabled={acting}>
                {acting ? 'Starting...' : 'Start New Season'}
              </ActionButton>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

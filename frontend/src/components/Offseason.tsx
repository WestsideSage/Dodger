import { useState } from 'react';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, PageHeader, StatChip, StatusMessage } from './ui';

interface OffseasonBeat {
  beat_index: number;
  total_beats: number;
  key: string;
  title: string;
  body: string;
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

  const progress = `${beat.beat_index + 1} / ${beat.total_beats}`;
  const stateLabel = beat.state.replace(/_/g, ' ');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <PageHeader
        eyebrow="Offseason"
        title={beat.title}
        description="Work through the off-season milestones to begin your next campaign."
        stats={
          <>
            <StatChip label="Beat" value={progress} />
            <StatChip label="Status" value={stateLabel} tone="info" />
          </>
        }
      />

      {error && (
        <StatusMessage title="Error" tone="danger">{error}</StatusMessage>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }} className="lg:grid-cols-[1.6fr_0.4fr]">
        {/* Beat narrative panel */}
        <div className="dm-panel" style={{ overflow: 'hidden' }}>
          <div
            className="dm-panel-header"
            style={{ borderBottom: '1px solid #1e293b', background: '#020617' }}
          >
            <p className="dm-kicker">Current beat</p>
            <h3 className="dm-panel-title">{beat.title}</h3>
          </div>
          <div
            style={{
              whiteSpace: 'pre-wrap',
              padding: '1.25rem',
              fontFamily: 'var(--font-body)',
              fontSize: '0.875rem',
              color: '#cbd5e1',
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            {beat.body}
          </div>
        </div>

        {/* Actions panel */}
        <div className="dm-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="dm-panel-header">
            <p className="dm-kicker">Offseason</p>
            <h3 className="dm-panel-title">Actions</h3>
            <p className="dm-panel-subtitle">Beat {beat.beat_index + 1} of {beat.total_beats}</p>
          </div>
          <div className="dm-section" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
            {beat.can_advance && (
              <ActionButton
                variant="primary"
                onClick={() => act('/api/offseason/advance')}
                disabled={acting}
              >
                {acting ? 'Advancing…' : 'Next Beat →'}
              </ActionButton>
            )}

            {beat.can_recruit && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
                  Sign the top available prospect to your roster before next season.
                </p>
                <ActionButton
                  variant="accent"
                  onClick={() => act('/api/offseason/recruit')}
                  disabled={acting}
                >
                  {acting ? 'Signing…' : 'Sign Best Rookie'}
                </ActionButton>
              </div>
            )}

            {beat.signed_player_id && !beat.can_recruit && (
              <StatusMessage title="Rookie signed" tone="success">
                A new player has joined your squad.
              </StatusMessage>
            )}

            {beat.can_begin_season && (
              <ActionButton
                variant="primary"
                onClick={() => act('/api/offseason/begin-season')}
                disabled={acting}
              >
                {acting ? 'Building schedule…' : 'Begin Next Season ▶'}
              </ActionButton>
            )}

            {!beat.can_advance && !beat.can_recruit && !beat.can_begin_season && (
              <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
                No actions available in this state.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

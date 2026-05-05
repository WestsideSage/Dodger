import { useCallback, useEffect, useState } from 'react';
import { ActionButton, Card, PageHeader, StatChip, StatusMessage } from './ui';

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
  const [beat, setBeat] = useState<OffseasonBeat | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBeat = useCallback((showLoading = false) => {
    if (showLoading) setLoading(true);
    return fetch('/api/offseason/beat')
      .then(res => {
        if (!res.ok) return res.json().then(d => Promise.reject(new Error(d.detail || 'Failed to load offseason')));
        return res.json();
      })
      .then(data => {
        setBeat(data);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => fetchBeat(true));
  }, [fetchBeat]);

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
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Off-season ceremony"
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

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.6fr_0.4fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-[var(--color-border)] bg-[var(--color-charcoal)] px-5 py-3">
            <h3 className="font-display uppercase tracking-widest text-sm text-[var(--color-paper)]">
              {beat.title}
            </h3>
          </div>
          <pre className="whitespace-pre-wrap p-5 font-mono text-sm text-[var(--color-charcoal)] leading-relaxed">
            {beat.body}
          </pre>
        </Card>

        <Card className="p-4 flex flex-col gap-3">
          <div>
            <h3 className="font-display uppercase tracking-widest text-sm text-[var(--color-charcoal)] mb-1">
              Actions
            </h3>
            <p className="text-xs text-[var(--color-muted)]">
              Beat {beat.beat_index + 1} of {beat.total_beats}
            </p>
          </div>

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
            <div className="flex flex-col gap-2">
              <p className="text-xs text-[var(--color-muted)]">
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
            <p className="text-xs text-[var(--color-muted)]">
              No actions available in this state.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

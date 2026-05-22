import { useState } from 'react';
import type { OffseasonBeat } from '../../types';
import { ActionButton, PageHeader } from '../ui';

type RecruitmentBeat = Extract<OffseasonBeat, { key: 'recruitment' }>;

export function RecruitmentChoice({
  beat,
  onSign,
  acting,
}: {
  beat: RecruitmentBeat;
  onSign: (prospectId: string) => void;
  acting: boolean;
}) {
  const prospects = beat.payload.available_prospects ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(
    prospects[0]?.prospect_id ?? null,
  );
  const selected = prospects.find(prospect => prospect.prospect_id === selectedId) ?? null;

  return (
    <section className="command-offseason-shell" data-testid="offseason-recruitment-action">
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title="Signing Day"
        description="Choose the rookie who joins your club for next season."
      />

      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker">Recruitment Desk</p>
        {prospects.length === 0 ? (
          <p className="command-offseason-copy">
            No prospects remain in the pool. Sign the best available talent to continue.
          </p>
        ) : (
          <div
            style={{
              display: 'grid',
              gap: '0.4rem',
              marginTop: '0.5rem',
              maxHeight: '420px',
              overflowY: 'auto',
            }}
          >
            {prospects.map(prospect => {
              const isSelected = prospect.prospect_id === selectedId;
              return (
                <button
                  key={prospect.prospect_id}
                  type="button"
                  data-testid="recruitment-prospect-row"
                  onClick={() => setSelectedId(prospect.prospect_id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.75rem',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.6rem 0.85rem',
                    background: isSelected ? 'rgba(34,211,238,0.1)' : '#0a1220',
                    border: '1px solid #1e293b',
                    borderLeft: `3px solid ${isSelected ? '#22d3ee' : '#1e293b'}`,
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <p style={{ margin: 0, color: '#f1f5f9', fontWeight: 700 }}>
                      {prospect.name}
                      {prospect.kind === 'free_agent' && (
                        <span
                          style={{
                            marginLeft: '0.45rem',
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            background: '#334155',
                            color: '#cbd5e1',
                            borderRadius: '3px',
                            padding: '1px 5px',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                          }}
                        >
                          Free Agent
                        </span>
                      )}
                    </p>
                    <p style={{ margin: '0.15rem 0 0', fontSize: '0.74rem', color: '#94a3b8' }}>
                      {prospect.archetype} · {prospect.hometown} · Age {prospect.age}
                    </p>
                  </div>
                  <div
                    className="dm-data"
                    style={{ fontSize: '1.15rem', fontWeight: 900, color: '#22d3ee' }}
                  >
                    {prospect.overall}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </article>

      <div className="dm-panel command-action-bar">
        <div>
          <p className="dm-kicker">Next action</p>
          <p>Recruitment must be resolved before the offseason ceremony can continue.</p>
        </div>
        <div className="command-action-buttons">
          <ActionButton
            variant="primary"
            onClick={() => onSign(selected?.prospect_id ?? '')}
            disabled={acting || (prospects.length > 0 && !selected)}
          >
            {acting
              ? 'Signing...'
              : selected
              ? `Sign ${selected.name}`
              : 'Sign Best Available'}
          </ActionButton>
        </div>
      </div>
    </section>
  );
}

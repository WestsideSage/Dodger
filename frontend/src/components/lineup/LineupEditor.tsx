import { useMemo, useState } from 'react';
import type { Player } from '../../types';
import { commandApi } from '../../api/client';
import { ApiError } from '../../api/client';
import { TermTip } from '../../legibility';
import { ActionButton } from '../ui';

const STARTERS_COUNT = 6;
const ROLE_LABELS = ['Captain', 'Striker', 'Anchor', 'Runner', 'Rookie', 'Utility'];

type Props = {
  roster: Player[];
  defaultLineup: string[];
  onClose: () => void;
  onSaved: (orderedPlayerIds: string[]) => void;
};

function reasonToMessage(reason: string): string {
  switch (reason) {
    case 'not_on_roster':
      return 'That player is not on this roster.';
    case 'duplicate':
      return 'A player cannot start in two slots.';
    case 'position_count':
      return `Lineup must have exactly ${STARTERS_COUNT} starters.`;
    default:
      return reason;
  }
}

export function LineupEditor({ roster, defaultLineup, onClose, onSaved }: Props) {
  const rosterById = useMemo(() => {
    const map = new Map<string, Player>();
    roster.forEach((player) => map.set(player.id, player));
    return map;
  }, [roster]);

  // Seed the starter slots from the resolved default lineup, dropping any
  // ids that have fallen off the roster. If the default is short, backfill
  // by highest OVR so the editor always opens with a legal 6.
  const initialStarters = useMemo(() => {
    const taken = new Set<string>();
    const slots: string[] = [];
    for (const id of defaultLineup) {
      if (slots.length >= STARTERS_COUNT) break;
      if (rosterById.has(id) && !taken.has(id)) {
        slots.push(id);
        taken.add(id);
      }
    }
    if (slots.length < STARTERS_COUNT) {
      const remaining = roster
        .filter((p) => !taken.has(p.id))
        .sort((a, b) => b.overall - a.overall);
      while (slots.length < STARTERS_COUNT && remaining.length > 0) {
        const next = remaining.shift()!;
        slots.push(next.id);
        taken.add(next.id);
      }
    }
    return slots;
  }, [defaultLineup, roster, rosterById]);

  const [starters, setStarters] = useState<string[]>(initialStarters);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorSlot, setErrorSlot] = useState<number | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  const benchPlayers = useMemo(() => {
    const starterSet = new Set(starters);
    return roster
      .filter((p) => !starterSet.has(p.id))
      .sort((a, b) => b.overall - a.overall);
  }, [roster, starters]);

  function commit(nextStarters: string[], offendingSlot: number | null = null) {
    setSaving(true);
    setError(null);
    setErrorSlot(null);
    setStatusNote(null);
    commandApi
      .saveLineup(nextStarters)
      .then((result) => {
        setStarters(nextStarters);
        setStatusNote('Saved.');
        onSaved(result.ordered_player_ids);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          setError(reasonToMessage(err.message));
          // Flash a red border on the slot the user just touched so the
          // violation is keyed visually to the offending row, then clear.
          if (
            offendingSlot !== null &&
            (err.message === 'not_on_roster' ||
              err.message === 'duplicate' ||
              err.message === 'position_count')
          ) {
            setErrorSlot(offendingSlot);
            setTimeout(() => setErrorSlot(null), 2000);
          }
        } else {
          setError('Failed to save lineup.');
        }
      })
      .finally(() => setSaving(false));
  }

  function handleSlotClick(slotIdx: number) {
    if (saving) return;
    setSelectedSlot((current) => (current === slotIdx ? null : slotIdx));
    setError(null);
    setErrorSlot(null);
  }

  function handleBenchClick(benchPlayerId: string) {
    if (saving) return;
    if (selectedSlot === null) {
      setError('Pick a starter slot first, then a bench player to swap in.');
      return;
    }
    const next = [...starters];
    const slotIdx = selectedSlot;
    next[slotIdx] = benchPlayerId;
    setSelectedSlot(null);
    commit(next, slotIdx);
  }

  function handleReset() {
    if (saving) return;
    setSaving(true);
    setError(null);
    setErrorSlot(null);
    setStatusNote(null);
    commandApi
      .clearLineup()
      .then((result) => {
        setStatusNote('Reset to auto-pick.');
        // Server returns the freshly-resolved auto-fill ordering so the
        // parent can update its cached roster view immediately.
        onSaved(result.ordered_player_ids ?? []);
        onClose();
      })
      .catch(() => setError('Failed to clear lineup override.'))
      .finally(() => setSaving(false));
  }

  return (
    <div
      role="dialog"
      aria-label="Lineup Editor"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
      onClick={onClose}
    >
      <div
        className="dm-panel"
        style={{
          width: '100%',
          maxWidth: '52rem',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderRadius: 8,
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: '1.25rem',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <span className="dm-kicker">Lineup</span>
            <h2
              style={{
                margin: 0,
                fontFamily: 'var(--font-display)',
                color: '#fff',
                fontSize: '1.5rem',
                textTransform: 'uppercase',
              }}
            >
              Manual Lineup Editor
            </h2>
            <div style={{ marginTop: '0.25rem', color: '#94a3b8', fontSize: '0.8rem', lineHeight: 1.5 }}>
              Click a starter slot, then a bench player to swap.{' '}
              <TermTip term="lineup.slot_order">Slot order</TermTip> sets role labels (Captain → Utility).
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              fontSize: '1.25rem',
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '1rem',
            padding: '1.25rem',
            overflowY: 'auto',
            flex: 1,
          }}
        >
          <div role="group" aria-label="Active starters — fielded six">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.5rem',
                paddingBottom: '0.35rem',
                borderBottom: '2px solid #22d3ee',
              }}
            >
              <span className="dm-kicker" style={{ color: '#22d3ee' }}>Active</span>
              <span
                style={{
                  background: '#22d3ee',
                  color: '#0b1220',
                  borderRadius: '3px',
                  fontWeight: 800,
                  fontSize: '0.6rem',
                  padding: '0.05rem 0.35rem',
                  letterSpacing: '0.04em',
                }}
                aria-label="Fielded six — exactly 6 starters"
              >
                {STARTERS_COUNT} fielded
              </span>
            </div>
            <div
              aria-label="Slot role order: Captain, Striker, Anchor, Runner, Rookie, Utility"
              style={{
                display: 'flex',
                gap: '0.3rem',
                flexWrap: 'wrap',
                marginBottom: '0.5rem',
              }}
            >
              {ROLE_LABELS.map((label, i) => (
                <span
                  key={label}
                  style={{
                    fontSize: '0.55rem',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                    color: i === 0 ? '#22d3ee' : '#64748b',
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '3px',
                    padding: '0.05rem 0.3rem',
                    textTransform: 'uppercase',
                  }}
                >
                  {i + 1}. {label}
                </span>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {starters.map((id, idx) => {
                const player = rosterById.get(id);
                const isSelected = selectedSlot === idx;
                const hasError = errorSlot === idx;
                return (
                  <button
                    key={`${id}-${idx}`}
                    type="button"
                    onClick={() => handleSlotClick(idx)}
                    disabled={saving}
                    aria-pressed={isSelected}
                    style={{
                      textAlign: 'left',
                      padding: '0.75rem',
                      borderRadius: 4,
                      background: isSelected ? '#0f4c5c' : '#0f172a',
                      border: hasError
                        ? '1px solid #ef4444'
                        : isSelected
                        ? '1px solid #22d3ee'
                        : '1px solid #1e293b',
                      borderLeft: hasError
                        ? '3px solid #ef4444'
                        : isSelected
                        ? '3px solid #22d3ee'
                        : '3px solid rgba(34,211,238,0.4)',
                      color: '#fff',
                      cursor: saving ? 'wait' : 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    <div className="dm-kicker">{ROLE_LABELS[idx] ?? `Slot ${idx + 1}`}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                      <span>{player ? player.name : id}</span>
                      <span style={{ color: '#94a3b8' }}>
                        {player ? `OVR ${player.overall}` : ''}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div role="group" aria-label="Bench players — not fielded">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.5rem',
                paddingBottom: '0.35rem',
                borderBottom: '1px solid #1e293b',
              }}
            >
              <span className="dm-kicker" style={{ color: '#64748b' }}>Bench</span>
              <span
                style={{
                  background: '#1e293b',
                  color: '#94a3b8',
                  borderRadius: '3px',
                  fontWeight: 700,
                  fontSize: '0.6rem',
                  padding: '0.05rem 0.35rem',
                  letterSpacing: '0.04em',
                }}
                aria-label={`${benchPlayers.length} bench players — not fielded`}
              >
                {benchPlayers.length} not fielded
              </span>
            </div>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
                maxHeight: '24rem',
                overflowY: 'auto',
              }}
            >
              {benchPlayers.length === 0 ? (
                <div style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                  No bench players available.
                </div>
              ) : (
                benchPlayers.map((player) => (
                  <button
                    key={player.id}
                    type="button"
                    onClick={() => handleBenchClick(player.id)}
                    disabled={saving || selectedSlot === null}
                    style={{
                      textAlign: 'left',
                      padding: '0.75rem',
                      borderRadius: 4,
                      background: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#fff',
                      cursor:
                        saving || selectedSlot === null ? 'not-allowed' : 'pointer',
                      opacity: selectedSlot === null ? 0.7 : 1,
                      fontFamily: 'inherit',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>{player.name}</span>
                      <span style={{ color: '#94a3b8' }}>OVR {player.overall}</span>
                    </div>
                    <div className="dm-kicker" style={{ marginTop: '0.25rem' }}>
                      {player.role}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        <div
          style={{
            padding: '0.75rem 1.25rem',
            borderTop: '1px solid #1e293b',
            background: '#0f172a',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.75rem',
          }}
        >
          <div style={{ fontSize: '0.85rem', minHeight: '1.25rem' }}>
            {error && <span style={{ color: '#ef4444' }}>{error}</span>}
            {!error && statusNote && <span style={{ color: '#22d3ee' }}>{statusNote}</span>}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={handleReset}
              disabled={saving}
              title="Let the lineup resolver pick the best six automatically. You can manually adjust after."
              aria-label="Auto-Pick: let lineup resolver choose the starting six"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                borderRadius: '4px',
                background: 'transparent',
                border: '1px solid #334155',
                color: '#94a3b8',
                fontSize: '0.78rem',
                fontWeight: 600,
                fontFamily: 'inherit',
                cursor: saving ? 'wait' : 'pointer',
                opacity: saving ? 0.6 : 1,
                transition: 'border-color 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => {
                if (!saving) {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = '#22d3ee';
                  (e.currentTarget as HTMLButtonElement).style.color = '#22d3ee';
                }
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = '#334155';
                (e.currentTarget as HTMLButtonElement).style.color = '#94a3b8';
              }}
            >
              ⚙ Auto-Pick
            </button>
            <ActionButton onClick={onClose}>Done</ActionButton>
          </div>
        </div>
      </div>
    </div>
  );
}

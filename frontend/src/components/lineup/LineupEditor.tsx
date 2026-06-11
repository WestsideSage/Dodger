import { useEffect, useMemo, useRef, useState } from 'react';
import type { Player } from '../../types';
import { commandApi } from '../../api/client';
import { ApiError } from '../../api/client';
import { TermTip } from '../../legibility';
import { ActionButton, Dialog } from '../ui';

const STARTERS_COUNT = 6;
const ROLE_LABELS = ['Captain', 'Striker', 'Anchor', 'Runner', 'Rookie', 'Utility'];

type Props = {
  roster: Player[];
  defaultLineup: string[];
  /** V19 Task 8: current state of the offseason auto-reorder toggle. */
  autoReorder: boolean;
  onClose: () => void;
  onSaved: (orderedPlayerIds: string[]) => void;
  /** Reflect toggle changes (explicit or implicit via manual save) upward. */
  onAutoReorderChange: (enabled: boolean) => void;
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

export function LineupEditor({
  roster,
  defaultLineup,
  autoReorder,
  onClose,
  onSaved,
  onAutoReorderChange,
}: Props) {
  const rosterById = useMemo(() => {
    const map = new Map<string, Player>();
    roster.forEach((player) => map.set(player.id, player));
    return map;
  }, [roster]);

  // Codex playtest issue 20: flag a stale six — the best benched player
  // out-rating the weakest fielded starter (common right after offseason
  // growth when auto-reorder is off).
  const staleNote = useMemo(() => {
    const fielded = defaultLineup.slice(0, STARTERS_COUNT)
      .map((id) => rosterById.get(id))
      .filter((p): p is Player => Boolean(p));
    if (fielded.length < STARTERS_COUNT) return null;
    const bench = roster.filter((p) => !defaultLineup.slice(0, STARTERS_COUNT).includes(p.id));
    if (bench.length === 0) return null;
    const weakest = [...fielded].sort((a, b) => a.overall - b.overall)[0];
    const best = [...bench].sort((a, b) => b.overall - a.overall)[0];
    if (best.overall > weakest.overall) {
      return `${best.name} (OVR ${best.overall}) is benched behind ${weakest.name} (OVR ${weakest.overall}) — Auto-Assign to re-seat the best six.`;
    }
    return null;
  }, [roster, defaultLineup, rosterById]);

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
  // WT-28 timer-cleanup: the offending-slot red flash auto-clears via setTimeout.
  // Track the id so closing the editor mid-flash clears it rather than calling
  // setState on an unmounted dialog.
  const errorSlotTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    return () => {
      if (errorSlotTimer.current !== null) clearTimeout(errorSlotTimer.current);
    };
  }, []);

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
        // A manual save flips the offseason auto-reorder off server-side —
        // say so the first time it actually changes, never silently.
        if (result.lineup_auto_reorder === false && autoReorder) {
          setStatusNote('Saved. Auto-reorder turned off — your lineup is hands-on now.');
          onAutoReorderChange(false);
        } else {
          setStatusNote('Saved.');
        }
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
            if (errorSlotTimer.current !== null) clearTimeout(errorSlotTimer.current);
            errorSlotTimer.current = setTimeout(() => setErrorSlot(null), 2000);
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

  function handleAutoAssign() {
    // V19 Task 8: one-shot CFB26-style Auto-assign — seats the optimal six
    // using the SAME optimizer the offseason auto-reorder runs, then leaves
    // the editor open for tweaks. A tool, not a mode change: the toggle is
    // untouched.
    if (saving) return;
    setSaving(true);
    setError(null);
    setErrorSlot(null);
    setStatusNote(null);
    commandApi
      .autoAssignLineup()
      .then((result) => {
        setStarters(result.ordered_player_ids.slice(0, STARTERS_COUNT));
        setStatusNote('Optimal six seated. Adjust freely — this was a one-shot.');
        onSaved(result.ordered_player_ids ?? []);
      })
      .catch(() => setError('Failed to auto-assign the lineup.'))
      .finally(() => setSaving(false));
  }

  function handleToggleAutoReorder() {
    if (saving) return;
    const next = !autoReorder;
    setSaving(true);
    setError(null);
    setStatusNote(null);
    commandApi
      .setLineupAutoReorder(next)
      .then((result) => {
        onAutoReorderChange(result.lineup_auto_reorder);
        setStatusNote(
          result.lineup_auto_reorder
            ? 'Auto-reorder ON — each offseason re-seats your best six.'
            : 'Auto-reorder OFF — your seats are yours; offseasons only remove retired players.',
        );
      })
      .catch(() => setError('Failed to update the auto-reorder setting.'))
      .finally(() => setSaving(false));
  }

  return (
    <Dialog
      label="Lineup Editor"
      onClose={onClose}
      panelClassName="dm-panel"
      panelStyle={{
        width: '100%',
        maxWidth: '52rem',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: 8,
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
      }}
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
          {/* WT-21: announce the lineup save outcome. Errors are asserted
              (role="alert"); the "Saved." / "Reset" note is polite
              (role="status"). Previously this was a silent coloured span. */}
          <div
            role={error ? 'alert' : 'status'}
            aria-live={error ? 'assertive' : 'polite'}
            style={{ fontSize: '0.85rem', minHeight: '1.25rem' }}
          >
            {error && <span style={{ color: '#ef4444' }}>{error}</span>}
            {!error && statusNote && <span style={{ color: '#22d3ee' }}>{statusNote}</span>}
            {/* Codex playtest issue 20: after offseason growth a hands-on
                lineup can silently go stale (a developed bench player
                out-rating a fielded starter). Persistent, computed warning —
                not a transient toast — so the player always knows. */}
            {!error && !statusNote && staleNote && (
              <span data-testid="lineup-stale-note" style={{ color: '#fbbf24' }}>{staleNote}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <label
              title="ON: each offseason re-seats your fielded six with the optimal lineup (set-and-forget). OFF: hands-on — offseasons only remove retired players and never re-rank a seat you chose. Saving a manual lineup turns this off automatically."
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                fontSize: '0.72rem',
                fontWeight: 600,
                color: autoReorder ? '#22d3ee' : '#94a3b8',
                cursor: saving ? 'wait' : 'pointer',
                whiteSpace: 'nowrap',
                userSelect: 'none',
              }}
            >
              <input
                type="checkbox"
                checked={autoReorder}
                onChange={handleToggleAutoReorder}
                disabled={saving}
                aria-label="Auto-reorder lineup each offseason"
                style={{ accentColor: '#22d3ee', cursor: 'inherit' }}
              />
              Auto-reorder each offseason
            </label>
            <button
              type="button"
              onClick={handleAutoAssign}
              disabled={saving}
              title="Seat the optimal six right now — the same logic the offseason auto-reorder uses. One-shot: doesn't change the toggle."
              aria-label="Auto-Assign: seat the optimal starting six now"
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
              ⚙ Auto-Assign
            </button>
            <ActionButton onClick={onClose}>Done</ActionButton>
          </div>
        </div>
    </Dialog>
  );
}

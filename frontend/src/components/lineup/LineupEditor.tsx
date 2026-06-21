import { useEffect, useMemo, useRef, useState } from 'react';
import type { Player } from '../../types';
import { commandApi } from '../../api/client';
import { ApiError } from '../../api/client';
import { TermTip } from '../../legibility';
import { ActionButton, Modal } from '../../ui';
import styles from './LineupEditor.module.css';

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
    <Modal label="Lineup Editor" onClose={onClose} panelClassName={styles.panel}>
        <div className={styles.header}>
          <div>
            <span className={styles.kicker}>Lineup</span>
            <h2 className={styles.title}>Manual Lineup Editor</h2>
            <div className={styles.subtitle}>
              Click a starter slot, then a bench player to swap.{' '}
              <TermTip term="lineup.slot_order">Slot order</TermTip> sets role labels (Captain → Utility).
            </div>
          </div>
          <button onClick={onClose} className={styles.closeBtn} aria-label="Close">×</button>
        </div>

        <div className={styles.body}>
          <div role="group" aria-label="Active starters — fielded six">
            <div className={`${styles.colHead} ${styles.colHeadActive}`}>
              <span className={`${styles.kicker} ${styles.kickerActive}`}>Active</span>
              <span
                className={`${styles.countTag} ${styles.countTagActive}`}
                aria-label="Fielded six — exactly 6 starters"
              >
                {STARTERS_COUNT} fielded
              </span>
            </div>
            <div
              aria-label="Slot role order: Captain, Striker, Anchor, Runner, Rookie, Utility"
              className={styles.roleRow}
            >
              {ROLE_LABELS.map((label, i) => (
                <span
                  key={label}
                  className={`${styles.roleChip} ${i === 0 ? styles.roleChipLead : ''}`.trim()}
                >
                  {i + 1}. {label}
                </span>
              ))}
            </div>
            <div className={styles.slotList}>
              {starters.map((id, idx) => {
                const player = rosterById.get(id);
                const isSelected = selectedSlot === idx;
                const hasError = errorSlot === idx;
                return (
                  <button
                    key={`${id}-${idx}`}
                    type="button"
                    data-testid={`lineup-slot-${idx}`}
                    onClick={() => handleSlotClick(idx)}
                    disabled={saving}
                    aria-pressed={isSelected}
                    className={`${styles.slot} ${isSelected ? styles.slotSelected : ''} ${hasError ? styles.slotError : ''}`.trim()}
                  >
                    <div className={styles.kicker}>{ROLE_LABELS[idx] ?? `Slot ${idx + 1}`}</div>
                    <div className={styles.slotTop}>
                      <span className={styles.slotName}>{player ? player.name : id}</span>
                      <span className={styles.slotOvr}>
                        {player ? `OVR ${player.overall}` : ''}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div role="group" aria-label="Bench players — not fielded">
            <div className={`${styles.colHead} ${styles.colHeadBench}`}>
              <span className={`${styles.kicker} ${styles.kickerBench}`}>Bench</span>
              <span
                className={`${styles.countTag} ${styles.countTagBench}`}
                aria-label={`${benchPlayers.length} bench players — not fielded`}
              >
                {benchPlayers.length} not fielded
              </span>
            </div>
            <div className={styles.benchScroll}>
              {benchPlayers.length === 0 ? (
                <div className={styles.benchEmpty}>
                  No bench players available.
                </div>
              ) : (
                benchPlayers.map((player) => (
                  <button
                    key={player.id}
                    type="button"
                    data-testid={`lineup-bench-${player.id}`}
                    onClick={() => handleBenchClick(player.id)}
                    disabled={saving || selectedSlot === null}
                    className={styles.bench}
                  >
                    <div className={styles.benchTop}>
                      <span className={styles.benchName}>{player.name}</span>
                      <span className={styles.benchOvr}>OVR {player.overall}</span>
                    </div>
                    <div className={`${styles.kicker} ${styles.benchRole}`}>
                      {player.role}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          {/* WT-21: announce the lineup save outcome. Errors are asserted
              (role="alert"); the "Saved." / "Reset" note is polite
              (role="status"). Previously this was a silent coloured span. */}
          <div
            role={error ? 'alert' : 'status'}
            aria-live={error ? 'assertive' : 'polite'}
            className={styles.status}
          >
            {error && <span className={styles.statusError}>{error}</span>}
            {!error && statusNote && <span className={styles.statusNote}>{statusNote}</span>}
            {/* Codex playtest issue 20: after offseason growth a hands-on
                lineup can silently go stale (a developed bench player
                out-rating a fielded starter). Persistent, computed warning —
                not a transient toast — so the player always knows. */}
            {!error && !statusNote && staleNote && (
              <span data-testid="lineup-stale-note" className={styles.staleNote}>{staleNote}</span>
            )}
          </div>
          <div className={styles.footerActions}>
            <label
              title="ON: each offseason re-seats your fielded six with the optimal lineup (set-and-forget). OFF: hands-on — offseasons only remove retired players and never re-rank a seat you chose. Saving a manual lineup turns this off automatically."
              className={`${styles.autoLabel} ${autoReorder ? styles.autoLabelOn : ''}`.trim()}
            >
              <input
                type="checkbox"
                checked={autoReorder}
                onChange={handleToggleAutoReorder}
                disabled={saving}
                aria-label="Auto-reorder lineup each offseason"
                className={styles.autoCheckbox}
              />
              Auto-reorder each offseason
            </label>
            <button
              type="button"
              onClick={handleAutoAssign}
              disabled={saving}
              title="Seat the optimal six right now — the same logic the offseason auto-reorder uses. One-shot: doesn't change the toggle."
              aria-label="Auto-Assign: seat the optimal starting six now"
              className={styles.autoAssign}
            >
              ⚙ Auto-Assign
            </button>
            <ActionButton onClick={onClose}>Done</ActionButton>
          </div>
        </div>
    </Modal>
  );
}

import type { KeyboardEvent } from 'react';
import type { CoachPolicy } from '../../../types';
import { useVoiceRegister } from '../../../hooks/useVoiceRegister';
import { StatusMessage } from '../../../ui';
import styles from './PolicyEditor.module.css';

type PolicyKey = keyof CoachPolicy;

const ROWS: Array<{
  key: PolicyKey;
  label: string;
  values: CoachPolicy[PolicyKey][];
  group?: 'opening-rush';
}> = [
  { key: 'approach', label: 'Approach', values: ['aggressive', 'patient', 'mixed'] },
  { key: 'target_focus', label: 'Target focus', values: ['their_stars', 'ball_holders', 'spread'] },
  { key: 'catch_posture', label: 'Catch posture', values: ['go_for_catches', 'play_safe', 'opportunistic'] },
  { key: 'rush_commit', label: 'Commit', values: ['all_in', 'balanced', 'hold_back'], group: 'opening-rush' },
  { key: 'rush_target', label: 'Target', values: ['nearest', 'strongest_side', 'center'], group: 'opening-rush' },
];

export function PolicyEditor({
  policy,
  disabled,
  error,
  onChange,
  officialRuleset,
}: {
  policy: CoachPolicy;
  disabled?: boolean;
  error?: string | null;
  onChange: (nextPolicy: CoachPolicy) => Promise<void> | void;
  // True on official-ruleset careers. Post-WT-20 the official engine
  // ENFORCES opening rush as disclosed sim-design (not a USA Dodgeball
  // rulebook mechanic) — the rush rows render the enforced note there. Rec
  // careers keep the Target-is-announced-only advisory (rec Target wiring is
  // a V19 backlog item).
  officialRuleset?: boolean;
}) {
  const { t } = useVoiceRegister(1);

  const handleKeyDown = (
    event: KeyboardEvent<HTMLDivElement>,
    row: typeof ROWS[number],
    currentValue: string,
  ) => {
    const currentIndex = row.values.indexOf(currentValue as CoachPolicy[typeof row.key]);
    if (currentIndex === -1) return;
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const delta = event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 1;
    const nextIndex = (currentIndex + delta + row.values.length) % row.values.length;
    void onChange({ ...policy, [row.key]: row.values[nextIndex] });
  };

  const coreRows = ROWS.filter((r) => r.group !== 'opening-rush');
  const rushRows = ROWS.filter((r) => r.group === 'opening-rush');

  const renderRow = (row: typeof ROWS[number]) => {
    const selectedValue = policy[row.key];
    const labelId = `policy-row-${row.key}`;
    const preview = t(`policy.${row.key}.${selectedValue}.preview`);

    return (
      <div key={row.key} className={styles.row}>
        <div
          role="radiogroup"
          aria-labelledby={labelId}
          onKeyDown={(event) => handleKeyDown(event, row, selectedValue)}
          className={styles.rowGroup}
        >
          {/* 4.7: selected state conveyed only by the highlighted pill + the
              preview line; the Phase 6 right-of-box label echo stays removed. */}
          <span id={labelId} className={styles.rowLabel}>
            {row.label}
          </span>
          <div className={styles.pillRow}>
            {row.values.map((value) => {
              const isSelected = value === selectedValue;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  disabled={disabled}
                  tabIndex={isSelected ? 0 : -1}
                  data-testid={`policy-${row.key}-${value}`}
                  onClick={() => void onChange({ ...policy, [row.key]: value })}
                  className={`${styles.pill}${isSelected ? ` ${styles.isSelected}` : ''}`}
                >
                  {isSelected && <span aria-hidden="true" className={styles.pillCheck}>✓</span>}
                  {t(`policy.${row.key}.${value}.label`)}
                </button>
              );
            })}
          </div>
          <p aria-live="polite" className={styles.preview}>
            {preview}
          </p>
          {/* V19a: the rec engine now resolves Target for real — it orders
              who SPRINTS at the opening whistle (Nearest = slot order,
              Strongest Side = power arms, Center = best overall), and only
              sprinters may take the opening-tick throws. The old
              announced-only advisory is retired because the knob is no
              longer dead. */}
          {row.key === 'rush_target' && !officialRuleset && (
            <p
              data-testid="rush-target-advisory-note"
              className={styles.advisory}
            >
              Resolved by the rec engine: Target orders who sprints at the opening whistle
              (slot order / power / overall), and sprinters take the opening throws.
            </p>
          )}
        </div>
      </div>
    );
  };

  return (
    <section
      data-testid="policy-editor"
      aria-disabled={disabled || undefined}
      className={`${styles.editor}${disabled ? ` ${styles.isDisabled}` : ''}`}
    >
      <div className={styles.header}>
        <div className={styles.headerMeta}>
          <p className={styles.kicker}>Policy Editor</p>
          <h4 className={styles.title}>Today&apos;s plan</h4>
          <p className={styles.subtitle}>
            Fine-tune the plan here. Changing the Weekly Intent resets these to that intent&apos;s preset.
          </p>
        </div>
        <span className={`${styles.statusBadge}${disabled ? '' : ` ${styles.isLive}`}`}>
          <span aria-hidden="true">{disabled ? '🔒' : '●'}</span>
          {disabled ? 'Locked' : 'Live'}
        </span>
      </div>

      {/* WT-21: the inline alert is now the shared StatusMessage primitive
          (tone="danger" -> role="alert" + aria-live="assertive"). Only the
          error surface is wrapped; the radiogroup below is left intact. */}
      {error && (
        <StatusMessage title="Plan not applied" tone="danger">
          {error}
        </StatusMessage>
      )}

      {/* Section-level lock signal: a banner the player cannot miss, plus a
          dimmed/non-interactive body — not just the header badge (Brief 4.7,
          criterion #4). */}
      {disabled && (
        <div className={styles.lockBanner}>
          <span aria-hidden="true">🔒</span>
          <span>Plan locked for this match — edits reopen next week.</span>
        </div>
      )}

      <div className={`${styles.rowBody}${disabled ? ` ${styles.isDisabled}` : ''}`}>
        {/* Core match plan — the three rows that govern the whole match. */}
        <div className={styles.coreRows}>
          {coreRows.map(renderRow)}
        </div>

        {/* Opening Rush — contained sub-section so the player sees these two
            rows govern only the match's first moment (Brief 4.7, criterion #2). */}
        <div className={styles.rushSection}>
          <div className={styles.rushHead}>
            <span aria-hidden="true" style={{ fontSize: '0.85rem' }}>⚡</span>
            <span className={styles.rushLabel}>Opening Rush</span>
            <span className={styles.rushSub}>· first moment only</span>
          </div>
          {officialRuleset && (
            <p
              data-testid="rush-enforced-sim-design-note"
              className={styles.enforcedNote}
            >
              Live on official careers: Commit shapes the opening exchange — an all-in
              rush&apos;s early throws are harder to catch, but its rushers catch worse on
              the counter — and Target picks which players secure your designated balls.
              This is Dodgeball Manager sim behavior, not a USA Dodgeball rulebook
              mechanic.
            </p>
          )}
          {rushRows.map(renderRow)}
        </div>
      </div>
    </section>
  );
}

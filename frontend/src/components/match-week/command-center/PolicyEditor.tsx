import type { KeyboardEvent } from 'react';
import type { CoachPolicy } from '../../../types';
import { useVoiceRegister } from '../../../hooks/useVoiceRegister';
import { StatusMessage } from '../../ui';

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
      <div key={row.key} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div
          role="radiogroup"
          aria-labelledby={labelId}
          onKeyDown={(event) => handleKeyDown(event, row, selectedValue)}
          style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}
        >
          {/* 4.7: selected state conveyed only by the highlighted pill + the
              preview line; the Phase 6 right-of-box label echo stays removed. */}
          <span id={labelId} style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '0.84rem' }}>
            {row.label}
          </span>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
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
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '0.45rem 0.8rem',
                    borderRadius: '999px',
                    border: `1.5px solid ${isSelected ? '#f97316' : '#334155'}`,
                    background: isSelected ? '#f97316' : '#0f172a',
                    color: isSelected ? '#0b1220' : '#cbd5e1',
                    fontWeight: isSelected ? 800 : 600,
                    fontSize: '0.76rem',
                    boxShadow: isSelected ? '0 0 0 3px rgba(249,115,22,0.18)' : 'none',
                    cursor: disabled ? 'default' : 'pointer',
                    transition: 'background 120ms, color 120ms, box-shadow 120ms',
                  }}
                >
                  {isSelected && <span aria-hidden="true" style={{ fontSize: '0.7rem', lineHeight: 1 }}>✓</span>}
                  {t(`policy.${row.key}.${value}.label`)}
                </button>
              );
            })}
          </div>
          <p
            aria-live="polite"
            style={{
              margin: 0,
              color: '#94a3b8',
              fontSize: '0.78rem',
              lineHeight: 1.45,
            }}
          >
            {preview}
          </p>
          {/* Disclosure parity with the official-rules note below: in the rec
              engine the Target choice only stamps the announced ball
              assignment into the match log — the opening rush is resolved
              from Commit (how many players sprint). Saying nothing here lets
              a dead knob pose as a decision. */}
          {row.key === 'rush_target' && !officialRuleset && (
            <p
              data-testid="rush-target-advisory-note"
              style={{
                margin: 0,
                color: '#64748b',
                fontSize: '0.7rem',
                lineHeight: 1.45,
              }}
            >
              Recorded as your announced assignment in the match log. The rec engine resolves
              the opening rush from Commit — Target does not change match outcomes yet.
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
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        padding: '0.9rem',
        border: `1px solid ${disabled ? '#1e293b' : '#243044'}`,
        borderRadius: '8px',
        background: '#08101f',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '1rem' }}>
        <div>
          <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Policy Editor</p>
          <h4 style={{ margin: 0, color: '#e2e8f0', fontSize: '1rem' }}>Today's plan</h4>
          <p style={{ margin: '0.3rem 0 0', color: '#64748b', fontSize: '0.72rem', maxWidth: '24rem' }}>
            Fine-tune the plan here. Changing the Weekly Intent resets these to that intent's preset.
          </p>
        </div>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.66rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            padding: '0.2rem 0.5rem',
            borderRadius: '999px',
            border: `1px solid ${disabled ? '#334155' : 'rgba(34,211,238,0.4)'}`,
            background: disabled ? '#0f172a' : 'rgba(34,211,238,0.1)',
            color: disabled ? '#64748b' : '#22d3ee',
            whiteSpace: 'nowrap',
          }}
        >
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
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            border: '1px dashed #334155',
            background: 'rgba(15,23,42,0.6)',
            color: '#94a3b8',
            fontSize: '0.76rem',
          }}
        >
          <span aria-hidden="true">🔒</span>
          <span>Plan locked for this match — edits reopen next week.</span>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          opacity: disabled ? 0.55 : 1,
          filter: disabled ? 'grayscale(0.35)' : 'none',
          transition: 'opacity 120ms',
        }}
      >
        {/* Core match plan — the three rows that govern the whole match. */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {coreRows.map(renderRow)}
        </div>

        {/* Opening Rush — contained sub-section so the player sees these two
            rows govern only the match's first moment (Brief 4.7, criterion #2). */}
        <div
          style={{
            borderRadius: '8px',
            border: '1px solid #1e293b',
            background: 'rgba(8,16,31,0.6)',
            padding: '0.75rem 0.8rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span aria-hidden="true" style={{ fontSize: '0.85rem' }}>⚡</span>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.62rem',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: '#cbd5e1',
              }}
            >
              Opening Rush
            </span>
            <span style={{ fontSize: '0.68rem', color: '#64748b' }}>· first moment only</span>
          </div>
          {officialRuleset && (
            <p
              data-testid="rush-enforced-sim-design-note"
              style={{
                margin: 0,
                padding: '0.4rem 0.55rem',
                borderRadius: '6px',
                border: '1px solid rgba(34,211,238,0.3)',
                background: 'rgba(34,211,238,0.06)',
                color: '#67e8f9',
                fontSize: '0.7rem',
                lineHeight: 1.45,
              }}
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

import type { KeyboardEvent } from 'react';
import type { CoachPolicy } from '../../../types';
import { useVoiceRegister } from '../../../hooks/useVoiceRegister';

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
}: {
  policy: CoachPolicy;
  disabled?: boolean;
  error?: string | null;
  onChange: (nextPolicy: CoachPolicy) => Promise<void> | void;
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

  return (
    <section
      data-testid="policy-editor"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        padding: '0.9rem',
        border: '1px solid #1e293b',
        borderRadius: '6px',
        background: '#08101f',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '1rem' }}>
        <div>
          <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Policy Editor</p>
          <h4 style={{ margin: 0, color: '#e2e8f0', fontSize: '1rem' }}>Today's plan</h4>
        </div>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.68rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: disabled ? '#64748b' : '#22d3ee',
          }}
        >
          {disabled ? 'Locked' : 'Live'}
        </span>
      </div>

      {error && (
        <p
          role="alert"
          style={{
            margin: 0,
            padding: '0.55rem 0.75rem',
            borderRadius: '4px',
            border: '1px solid rgba(244,63,94,0.35)',
            background: 'rgba(69,10,10,0.65)',
            color: '#fecdd3',
            fontSize: '0.8rem',
          }}
        >
          {error}
        </p>
      )}

      {ROWS.map((row, index) => {
        const selectedValue = policy[row.key];
        const isOpeningRushStart = row.group === 'opening-rush' && ROWS[index - 1]?.group !== 'opening-rush';
        const labelId = `policy-row-${row.key}`;
        const preview = t(`policy.${row.key}.${selectedValue}.preview`);

        return (
          <div key={row.key} style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {isOpeningRushStart && (
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '0.62rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#94a3b8',
                }}
              >
                Opening rush
              </span>
            )}
            <div
              role="radiogroup"
              aria-labelledby={labelId}
              onKeyDown={(event) => handleKeyDown(event, row, selectedValue)}
              style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}
            >
              {/* 4.7: the selected option is conveyed by the highlighted pill
                  below and described by the preview line; the former
                  right-of-box echo of the same label was the redundant third
                  showing per category, so it is removed (de-dup at the data
                  boundary; visual restyle deferred to Phase 8). */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '1rem' }}>
                <span id={labelId} style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '0.84rem' }}>
                  {row.label}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
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
                        padding: '0.45rem 0.75rem',
                        borderRadius: '999px',
                        border: `1px solid ${isSelected ? '#f97316' : '#334155'}`,
                        background: isSelected ? 'rgba(249,115,22,0.18)' : '#0f172a',
                        color: isSelected ? '#fde68a' : '#cbd5e1',
                        fontWeight: 700,
                        fontSize: '0.76rem',
                        cursor: disabled ? 'default' : 'pointer',
                      }}
                    >
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
            </div>
          </div>
        );
      })}
    </section>
  );
}

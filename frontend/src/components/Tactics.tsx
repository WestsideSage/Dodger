import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { CoachPolicy } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, Badge, PageHeader, StatChip, StatusMessage } from './ui';

// Per-tendency value display color
const tendencyColor: Partial<Record<keyof CoachPolicy, string>> = {
  target_stars: '#f97316',       // orange — offensive targeting
  target_ball_holder: '#f97316', // orange — offensive targeting
  rush_frequency: '#f97316',     // orange — aggression
  rush_proximity: '#f97316',     // orange — aggression
  tempo: '#f97316',              // orange — action
  risk_tolerance: '#f59e0b',     // amber — risk/fatigue
  sync_throws: '#22d3ee',        // cyan — coordination / conservative
  catch_bias: '#22d3ee',         // cyan — defensive preference
};

const tacticGroups: Array<{
  title: string;
  description: string;
  fields: Array<{
    key: keyof CoachPolicy;
    label: string;
    leftLabel: string;
    rightLabel: string;
    description: string;
  }>;
}> = [
  {
    title: 'Targeting',
    description: 'Who gets pressured first.',
    fields: [
      {
        key: 'target_stars',
        label: 'Target Stars',
        leftLabel: 'Weakest',
        rightLabel: 'Best Players',
        description: "Focus throws on the opponent's strongest players.",
      },
      {
        key: 'target_ball_holder',
        label: 'Target Ball Holder',
        leftLabel: 'Ignore',
        rightLabel: 'Prioritize',
        description: 'Focus throws on opponents currently holding balls.',
      },
    ],
  },
  {
    title: 'Risk and timing',
    description: 'How much patience the club shows.',
    fields: [
      {
        key: 'risk_tolerance',
        label: 'Risk Tolerance',
        leftLabel: 'Safe Play',
        rightLabel: 'High Risk',
        description: 'Willingness to make risky throws or plays.',
      },
      {
        key: 'sync_throws',
        label: 'Sync Throws',
        leftLabel: 'Individual',
        rightLabel: 'Coordinated',
        description: 'Tendency to wait and throw together with teammates.',
      },
      {
        key: 'tempo',
        label: 'Tempo',
        leftLabel: 'Slow',
        rightLabel: 'Fast',
        description: 'Overall speed of decision making and throwing.',
      },
    ],
  },
  {
    title: 'Court posture',
    description: 'Space control and defensive instincts.',
    fields: [
      {
        key: 'rush_frequency',
        label: 'Rush Frequency',
        leftLabel: 'Stay Back',
        rightLabel: 'Aggressive',
        description: 'How often players will rush the center line.',
      },
      {
        key: 'rush_proximity',
        label: 'Rush Proximity',
        leftLabel: 'Distant',
        rightLabel: 'Close Range',
        description: 'How close players get to the center line when rushing.',
      },
      {
        key: 'catch_bias',
        label: 'Catch Bias',
        leftLabel: 'Dodge',
        rightLabel: 'Attempt Catch',
        description: 'Preference for attempting catches over dodging.',
      },
    ],
  },
];

// Inline coaching-board slider — renders dm-tactic-slider with per-tendency value color
function TacticSlider({
  label,
  value,
  onChange,
  leftLabel = 'Low',
  rightLabel = 'High',
  description,
  valueColor = '#cbd5e1',
}: {
  label: string;
  value: number;
  onChange: (val: number) => void;
  leftLabel?: string;
  rightLabel?: string;
  description?: string;
  valueColor?: string;
}) {
  const percentage = Math.round(value * 100);
  const setClampedValue = (nextValue: number) => onChange(Math.min(1, Math.max(0, nextValue)));
  const handleChange = (nextValue: string) => setClampedValue(parseFloat(nextValue));
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const step = event.shiftKey ? 0.1 : 0.01;
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
      event.preventDefault();
      setClampedValue(value + step);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
      event.preventDefault();
      setClampedValue(value - step);
    } else if (event.key === 'Home') {
      event.preventDefault();
      setClampedValue(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      setClampedValue(1);
    }
  };

  return (
    <div className="dm-tactic-slider">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
        <label
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '0.875rem',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: '#cbd5e1',
          }}
        >
          {label}
        </label>
        <span className="dm-data" style={{ fontSize: '0.875rem', color: valueColor, fontWeight: 600 }}>
          {percentage}%
        </span>
      </div>
      {description && (
        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem', marginBottom: '0.5rem', fontFamily: 'var(--font-body)' }}>
          {description}
        </p>
      )}
      <div style={{ position: 'relative', paddingTop: '0.5rem' }}>
        <input
          aria-label={label}
          data-testid={`tactic-${label.toLowerCase().replaceAll(' ', '-')}`}
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onInput={(e) => handleChange(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          className="tactic-range"
          style={{ width: '100%', cursor: 'pointer' }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: '0.25rem',
            fontSize: '0.625rem',
            textTransform: 'uppercase',
            color: '#475569',
            fontFamily: 'var(--font-mono-data)',
            letterSpacing: '0.08em',
          }}
        >
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      </div>
    </div>
  );
}

export function Tactics() {
  const { data, loading, error, setData, setError } = useApiResource<CoachPolicy>('/api/tactics');
  const [saving, setSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const handleSave = () => {
    if (!data || !isDirty) return;
    setSaving(true);
    setSavedMessage(null);
    setError(null);
    fetch('/api/tactics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to save tactics');
        return res.json();
      })
      .then(() => {
        setIsDirty(false);
        setSavedMessage('Tactics saved.');
      })
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const updatePolicy = (key: keyof CoachPolicy, value: number) => {
    setData(prev => prev ? { ...prev, [key]: value } : null);
    setIsDirty(true);
    setSavedMessage(null);
  };

  if (loading) return <StatusMessage title="Loading tactics">Opening the coach board.</StatusMessage>;
  if (error) return <StatusMessage title="Tactics unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No tactics">No coach policy returned.</StatusMessage>;

  const averageIntent = Math.round((Object.values(data).reduce((sum, value) => sum + value, 0) / Object.values(data).length) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Page header — kicker / title / save controls */}
      <div className="dm-panel">
        <PageHeader
          eyebrow="Coach room"
          title="Coaching Board"
          description="Adjust team tendencies and match strategy. Changes apply to the next match."
          stats={
            <>
              <StatChip label="Intent" value={`${averageIntent}%`} tone="info" />
              <Badge tone={isDirty ? 'warning' : 'success'}>{isDirty ? 'Unsaved' : 'Saved'}</Badge>
              <ActionButton onClick={handleSave} disabled={saving || !isDirty} variant="primary">
                {saving ? 'Saving...' : isDirty ? 'Save Tactics' : 'Saved'}
              </ActionButton>
            </>
          }
        />
      </div>

      {savedMessage && <StatusMessage title="Saved" tone="success">{savedMessage}</StatusMessage>}

      {/* Tactic group panels */}
      {tacticGroups.map(group => (
        <div key={group.title} className="dm-panel">
          <div className="dm-panel-header" style={{ marginBottom: '1rem' }}>
            <p className="dm-kicker">Tactics</p>
            <h3 className="dm-panel-title">{group.title}</h3>
            <p className="dm-panel-subtitle">{group.description}</p>
          </div>
          <div className="dm-section">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0' }}>
              {group.fields.map(field => (
                <TacticSlider
                  key={field.key}
                  label={field.label}
                  value={data[field.key]}
                  onChange={(value) => updatePolicy(field.key, value)}
                  leftLabel={field.leftLabel}
                  rightLabel={field.rightLabel}
                  description={field.description}
                  valueColor={tendencyColor[field.key] ?? '#cbd5e1'}
                />
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

import { useState } from 'react';
import type { CoachPolicy } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { ActionButton, Badge, PageHeader, StatChip, StatusMessage, TendencySlider } from './ui';

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
    <div className="flex max-w-4xl flex-col gap-5">
      <PageHeader
        eyebrow="Coach room"
        title="Coach Policy"
        description="Grouped sliders keep tactical intent readable while preserving the eight-field policy model."
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

      {savedMessage && <StatusMessage title="Saved" tone="success">{savedMessage}</StatusMessage>}

      <div className="grid grid-cols-1 gap-4">
        {tacticGroups.map(group => (
          <section key={group.title} className="rounded-md border border-[var(--color-border)] bg-[var(--color-cream)] p-4 shadow-[var(--shadow-panel)]">
            <div className="mb-4 flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
              <div>
                <h3 className="font-display uppercase tracking-widest text-lg text-[var(--color-charcoal)]">{group.title}</h3>
                <p className="text-sm text-[var(--color-muted)]">{group.description}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {group.fields.map(field => (
                <TendencySlider
                  key={field.key}
                  label={field.label}
                  value={data[field.key]}
                  onChange={(value) => updatePolicy(field.key, value)}
                  leftLabel={field.leftLabel}
                  rightLabel={field.rightLabel}
                  description={field.description}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import type { CommandCenterResponse, CommandCenterSimResponse } from '../types';
import { ActionButton, Badge, Card, KeyValueRow, PageHeader, StatChip, StatusMessage } from './ui';

const devFocusOptions = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

const departmentLabels: Record<string, string> = {
  tactics: 'Tactics',
  training: 'Training',
  conditioning: 'Conditioning',
  medical: 'Medical',
  scouting: 'Scouting',
  culture: 'Culture',
};

function formatTactic(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function CommandCenter({ onOpenReplay }: { onOpenReplay?: (matchId: string) => void }) {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [selectedIntent, setSelectedIntent] = useState('Win Now');
  const [selectedDevFocus, setSelectedDevFocus] = useState('BALANCED');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<CommandCenterSimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = (showLoading = false) => {
    if (showLoading) setLoading(true);
    return fetch('/api/command-center')
      .then(res => {
        if (!res.ok) throw new Error('Command center unavailable');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    fetch('/api/command-center')
      .then(res => {
        if (!res.ok) throw new Error('Command center unavailable');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        if (cancelled) return;
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const savePlan = (intent = selectedIntent, devFocus = selectedDevFocus) => {
    setSaving(true);
    setError(null);
    return fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, department_orders: { dev_focus: devFocus } }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Plan save failed');
        return res.json();
      })
      .then((payload: CommandCenterResponse) => {
        setData(payload);
        setSelectedIntent(payload.plan.intent);
        setSelectedDevFocus(payload.plan.department_orders?.dev_focus ?? 'BALANCED');
      })
      .catch(err => setError(err.message))
      .finally(() => setSaving(false));
  };

  const simulate = () => {
    setSimulating(true);
    setError(null);
    fetch('/api/command-center/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent: selectedIntent }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Command simulation failed');
        return res.json();
      })
      .then((payload: CommandCenterSimResponse) => {
        setResult(payload);
        return load();
      })
      .catch(err => setError(err.message))
      .finally(() => setSimulating(false));
  };

  if (loading && !data) return <StatusMessage title="Loading command center">Opening the weekly desk.</StatusMessage>;
  if (error) return <StatusMessage title="Command center unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;

  const plan = data.plan;
  const dashboard = result?.dashboard || data.latest_dashboard;

  return (
    <div className="flex flex-col gap-5" data-testid="weekly-command-center">
      <PageHeader
        eyebrow="Weekly command center"
        title="Command Center"
        description={data.current_objective}
        stats={
          <>
            <StatChip label="Week" value={data.week} tone="warning" />
            <StatChip label="Club" value={data.player_club_name} />
            <StatChip label="Opponent" value={plan.opponent.name} tone="info" />
          </>
        }
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="p-4">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-display uppercase tracking-widest text-lg">Weekly Plan</h3>
              <p className="text-sm text-[var(--color-muted)]">Set the program intent, then accept the staff plan or adjust supporting tabs.</p>
            </div>
            <Badge tone="success">Playable</Badge>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Intent</span>
              <select
                aria-label="Weekly intent"
                value={selectedIntent}
                onChange={(event) => {
                  setSelectedIntent(event.target.value);
                  savePlan(event.target.value, selectedDevFocus);
                }}
                className="mt-1 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] px-3 py-2 font-bold text-[var(--color-charcoal)]"
              >
                {plan.available_intents.map(intent => <option key={intent}>{intent}</option>)}
              </select>
            </label>

            <label className="block">
              <span className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Dev Focus</span>
              <select
                aria-label="Development Focus"
                value={selectedDevFocus}
                onChange={(event) => {
                  setSelectedDevFocus(event.target.value);
                  savePlan(selectedIntent, event.target.value);
                }}
                className="mt-1 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] px-3 py-2 font-bold text-[var(--color-charcoal)]"
              >
                {devFocusOptions.map(focus => <option key={focus} value={focus}>{focus.replace(/_/g, ' ')}</option>)}
              </select>
            </label>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {Object.entries(plan.department_orders).filter(([key]) => key !== 'dev_focus').map(([key, value]) => (
              <div key={key} className="rounded-md border border-[var(--color-border)] bg-[var(--color-cream)] p-3">
                <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">{departmentLabels[key] || key}</div>
                <div className="mt-1 font-bold capitalize">{value}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <ActionButton variant="primary" onClick={() => savePlan()} disabled={saving || simulating}>
              {saving ? 'Saving...' : 'Accept Recommended Plan'}
            </ActionButton>
            <ActionButton variant="accent" onClick={simulate} disabled={simulating || saving} data-testid="simulate-command-week">
              {simulating ? 'Simulating...' : 'Simulate Command Week'}
            </ActionButton>
            <ActionButton variant="ghost" onClick={() => load(true)} disabled={loading || simulating}>
              Refresh
            </ActionButton>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-display uppercase tracking-widest text-lg">Staff Room</h3>
          <div className="mt-3 flex flex-col gap-3">
            {plan.recommendations.map(item => (
              <div key={item.department} className="rounded-md border border-[var(--color-line)] p-3">
                <div className="flex items-center justify-between gap-3">
                  <strong className="font-display uppercase tracking-wider text-xs">{item.department}</strong>
                  <span className="text-xs text-[var(--color-muted)]">{item.voice}</span>
                </div>
                <p className="mt-2 text-sm text-[var(--color-charcoal)]">{item.text}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="p-4">
          <h3 className="font-display uppercase tracking-widest text-lg">Lineup Accountability</h3>
          <p className="mt-1 text-sm text-[var(--color-muted)]">{plan.lineup.summary}</p>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {plan.lineup.players.map(player => (
              <div key={player.id} className="rounded-md border border-[var(--color-line)] px-3 py-2">
                <div className="font-bold">{player.name}</div>
                <div className="text-xs text-[var(--color-muted)]">OVR {player.overall} · Potential {player.potential ?? 'n/a'}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-col gap-2">
            {plan.warnings.map(warning => <StatusMessage key={warning} title="Staff warning" tone="warning">{warning}</StatusMessage>)}
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-display uppercase tracking-widest text-lg">Tactics Evidence</h3>
          <div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-1">
            <KeyValueRow label="Target stars" value={formatTactic(plan.tactics.target_stars)} />
            <KeyValueRow label="Ball holder" value={formatTactic(plan.tactics.target_ball_holder)} />
            <KeyValueRow label="Rush freq." value={formatTactic(plan.tactics.rush_frequency)} />
            <KeyValueRow label="Catch bias" value={formatTactic(plan.tactics.catch_bias)} />
          </div>
          <p className="mt-3 text-sm text-[var(--color-muted)]">
            Dashboard notes only cite effects that are tracked in the saved plan or match stats.
          </p>
        </Card>
      </div>

      {dashboard && (
        <Card className="overflow-hidden" data-testid="post-week-dashboard">
          <div className="border-b border-[var(--color-border)] bg-[var(--color-charcoal)] p-4 text-[var(--color-paper)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-display uppercase tracking-widest text-lg">Post-Week Dashboard</h3>
                <p className="text-sm text-[color-mix(in_srgb,var(--color-paper)_78%,transparent)]">
                  Week {dashboard.week} · {dashboard.result} vs {dashboard.opponent_name}
                </p>
              </div>
              <Badge tone={dashboard.result === 'Win' ? 'success' : dashboard.result === 'Loss' ? 'danger' : 'warning'}>{dashboard.result}</Badge>
              {dashboard.match_id && onOpenReplay && (
                <ActionButton variant="accent" onClick={() => onOpenReplay(dashboard.match_id)}>
                  Open Replay Proof
                </ActionButton>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 p-4 lg:grid-cols-5">
            {dashboard.lanes.map(lane => (
              <section key={lane.title} className="rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] p-3">
                <h4 className="font-display uppercase tracking-wider text-xs text-[var(--color-brick)]">{lane.title}</h4>
                <p className="mt-2 text-sm font-bold">{lane.summary}</p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[var(--color-muted)]">
                  {lane.items.map(item => <li key={item}>{item}</li>)}
                </ul>
              </section>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display uppercase tracking-widest text-lg">Command History</h3>
          <Badge tone="info">{data.history.length} records</Badge>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
          {data.history.slice(-6).reverse().map(record => (
            <div key={record.history_id} className="rounded-md border border-[var(--color-line)] p-3">
              <div className="flex justify-between gap-3">
                <strong>Week {record.week}</strong>
                <span className="text-xs text-[var(--color-muted)]">{record.intent}</span>
              </div>
              <p className="mt-1 text-sm">{record.dashboard.result} vs {record.dashboard.opponent_name}</p>
              {record.match_id && onOpenReplay && (
                <button
                  type="button"
                  onClick={() => onOpenReplay(record.match_id as string)}
                  className="mt-3 font-display text-xs uppercase tracking-wider text-[var(--color-brick)]"
                >
                  Open replay proof
                </button>
              )}
            </div>
          ))}
          {!data.history.length && <p className="text-sm text-[var(--color-muted)]">No command weeks simulated yet.</p>}
        </div>
      </Card>
    </div>
  );
}

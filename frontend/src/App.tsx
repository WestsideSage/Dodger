import { useEffect, useState } from 'react';
import { CommandCenter } from './components/CommandCenter';
import { Hub } from './components/Hub';
import { DynastyOffice } from './components/DynastyOffice';
import { NewsWire, Schedule, Standings } from './components/LeagueContext';
import { Offseason } from './components/Offseason';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
import { Tactics } from './components/Tactics';
import { MatchReplay } from './components/MatchReplay';
import type { MatchReplayResponse } from './types';

type Screen = 'loading' | 'menu' | 'game' | 'offseason';
type Tab = 'command' | 'hub' | 'dynasty' | 'roster' | 'tactics' | 'standings' | 'schedule' | 'news';

const OFFSEASON_STATES = new Set([
  'season_complete_offseason_beat',
  'season_complete_recruitment_pending',
  'next_season_ready',
]);

const tabs: Array<{ id: Tab; label: string; short: string }> = [
  { id: 'command', label: 'Command Center', short: 'Week' },
  { id: 'hub', label: 'Hub', short: 'Ops' },
  { id: 'dynasty', label: 'Dynasty Office', short: 'Program' },
  { id: 'roster', label: 'Roster', short: 'Team' },
  { id: 'tactics', label: 'Tactics', short: 'Policy' },
  { id: 'standings', label: 'Standings', short: 'Table' },
  { id: 'schedule', label: 'Schedule', short: 'Fixtures' },
  { id: 'news', label: 'News', short: 'Wire' },
];

function tabFromUrl(): Tab {
  const tab = new URLSearchParams(window.location.search).get('tab');
  return tabs.some(item => item.id === tab) ? tab as Tab : 'command';
}

function App() {
  const [screen, setScreen] = useState<Screen>('loading');
  const [activeTab, setActiveTab] = useState<Tab>(tabFromUrl);
  const [commandReplay, setCommandReplay] = useState<MatchReplayResponse | null>(null);
  const [commandReplayLoading, setCommandReplayLoading] = useState(false);

  useEffect(() => {
    fetch('/api/save-state')
      .then((r) => r.json())
      .then((data) => {
        if (!data.loaded) { setScreen('menu'); return; }
        return fetch('/api/status').then(r => r.json()).then(status => {
          const state = status?.state?.state ?? '';
          setScreen(OFFSEASON_STATES.has(state) ? 'offseason' : 'game');
        });
      })
      .catch(() => setScreen('menu'));
  }, []);

  useEffect(() => {
    if (screen !== 'game') return;
    const params = new URLSearchParams(window.location.search);
    params.set('tab', activeTab);
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
  }, [activeTab, screen]);

  const openCommandReplay = (matchId: string) => {
    setCommandReplayLoading(true);
    fetch(`/api/matches/${encodeURIComponent(matchId)}/replay`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch match replay');
        return res.json();
      })
      .then(setCommandReplay)
      .finally(() => setCommandReplayLoading(false));
  };

  if (screen === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-canvas)]">
        <p className="font-display uppercase tracking-widest text-[var(--color-muted)]">Loading…</p>
      </div>
    );
  }

  if (screen === 'menu') {
    return <SaveMenu onSaveLoaded={() => window.location.reload()} />;
  }

  if (screen === 'offseason') {
    return (
      <div className="app-shell min-h-screen">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-4 md:px-8 md:py-6">
          <header className="site-header">
            <div>
              <p className="font-display uppercase tracking-[0.22em] text-xs text-[var(--color-brick)]">Off-season</p>
              <h1 className="font-display uppercase tracking-widest text-4xl md:text-5xl text-[var(--color-charcoal)]">
                Dodgeball Manager
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  fetch('/api/saves/unload', { method: 'POST' })
                    .finally(() => window.location.reload());
                }}
                title="Back to Save Menu"
                className="rounded border border-[var(--color-border)] px-3 py-1.5 text-xs font-display uppercase tracking-wider text-[var(--color-muted)] hover:text-[var(--color-charcoal)] hover:border-[var(--color-charcoal)] transition-colors"
              >
                Menu
              </button>
            </div>
          </header>
          <main className="workspace-panel">
            <Offseason />
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell min-h-screen">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-4 md:px-8 md:py-6">
        <header className="site-header">
          <div>
            <p className="font-display uppercase tracking-[0.22em] text-xs text-[var(--color-brick)]">Dynasty simulator</p>
            <h1 className="font-display uppercase tracking-widest text-4xl md:text-5xl text-[var(--color-charcoal)]">
              Dodgeball Manager
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] px-4 py-3 text-right shadow-[var(--shadow-panel)] md:block">
              <div className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">Weekly loop</div>
              <div className="font-bold">V5 command center</div>
            </div>
            <button
              onClick={() => {
                fetch('/api/saves/unload', { method: 'POST' })
                  .finally(() => window.location.reload());
              }}
              title="Back to Save Menu"
              className="rounded border border-[var(--color-border)] px-3 py-1.5 text-xs font-display uppercase tracking-wider text-[var(--color-muted)] hover:text-[var(--color-charcoal)] hover:border-[var(--color-charcoal)] transition-colors"
            >
              Menu
            </button>
          </div>
        </header>

        <nav className="nav-rail" aria-label="Primary">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`nav-tab ${activeTab === tab.id ? 'nav-tab-active' : ''}`}
            >
              <span>{tab.label}</span>
              <small>{tab.short}</small>
            </button>
          ))}
        </nav>

        <main className="workspace-panel">
          {commandReplay && (
            <MatchReplay
              replay={commandReplay}
              acknowledging={false}
              onAcknowledge={() => setCommandReplay(null)}
            />
          )}
          {!commandReplay && commandReplayLoading && (
            <p className="font-display uppercase tracking-widest text-[var(--color-muted)]">Loading replay…</p>
          )}
          {!commandReplay && !commandReplayLoading && activeTab === 'command' && <CommandCenter onOpenReplay={openCommandReplay} />}
          {!commandReplay && !commandReplayLoading && activeTab === 'hub' && <Hub />}
          {!commandReplay && !commandReplayLoading && activeTab === 'dynasty' && <DynastyOffice />}
          {!commandReplay && !commandReplayLoading && activeTab === 'roster' && <Roster />}
          {!commandReplay && !commandReplayLoading && activeTab === 'tactics' && <Tactics />}
          {!commandReplay && !commandReplayLoading && activeTab === 'standings' && <Standings />}
          {!commandReplay && !commandReplayLoading && activeTab === 'schedule' && <Schedule />}
          {!commandReplay && !commandReplayLoading && activeTab === 'news' && <NewsWire />}
        </main>
      </div>
    </div>
  );
}

export default App;

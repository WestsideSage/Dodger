import { useEffect, useState } from 'react';
import { CommandCenter } from './components/CommandCenter';
import { Hub } from './components/Hub';
import { DynastyOffice } from './components/DynastyOffice';
import { NewsWire, Schedule, Standings } from './components/LeagueContext';
import { Offseason } from './components/Offseason';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
import { Tactics } from './components/Tactics';
import MatchReplay from './components/MatchReplay';
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

const tabKickers: Record<Tab, string> = {
  command: 'WAR ROOM',
  hub: 'WAR ROOM',
  dynasty: 'WAR ROOM',
  roster: 'ROSTER LAB',
  tactics: 'WAR ROOM',
  standings: 'LEAGUE OFFICE',
  schedule: 'LEAGUE OFFICE',
  news: 'LEAGUE OFFICE',
};

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
      <div className="dm-app-shell" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p className="dm-kicker" style={{ fontSize: '0.875rem', letterSpacing: '0.2em' }}>Loading…</p>
      </div>
    );
  }

  if (screen === 'menu') {
    return <SaveMenu onSaveLoaded={() => window.location.reload()} />;
  }

  const menuButton = (
    <button
      onClick={() => {
        fetch('/api/saves/unload', { method: 'POST' })
          .finally(() => window.location.reload());
      }}
      title="Back to Save Menu"
      style={{
        width: '100%',
        padding: '0.5rem 0.75rem',
        background: 'transparent',
        border: '1px solid #1e293b',
        borderRadius: '4px',
        color: '#64748b',
        fontFamily: 'var(--font-display)',
        fontSize: '0.6875rem',
        textTransform: 'uppercase' as const,
        letterSpacing: '0.1em',
        cursor: 'pointer',
        textAlign: 'left' as const,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#cbd5e1'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#334155'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#64748b'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#1e293b'; }}
    >
      <span className="dm-nav-dot" />
      Menu
    </button>
  );

  if (screen === 'offseason') {
    return (
      <div className="dm-app-shell flex" style={{ minHeight: '100vh' }}>
        {/* Left Navigation Rail */}
        <aside className="dm-left-nav">
          <div className="dm-left-nav-logo">
            <p className="dm-kicker">Dodgeball Manager</p>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0 }}>2026</p>
          </div>
          <nav style={{ padding: '0.5rem 0', flex: 1 }} aria-label="Primary">
            <div className="dm-nav-item dm-nav-item-active" style={{ cursor: 'default' }}>
              <span className="dm-nav-dot" />
              Off-Season
            </div>
          </nav>
          <div style={{ padding: '0.75rem', borderTop: '1px solid #1e293b' }}>
            {menuButton}
          </div>
        </aside>

        {/* Main workspace */}
        <div className="dm-workspace">
          <header className="dm-broadcast-header">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
              <div>
                <p className="dm-kicker">OFF-SEASON</p>
                <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0 }}>
                  Dodgeball Manager
                </h1>
              </div>
            </div>
          </header>
          <div className="dm-content">
            <Offseason />
          </div>
        </div>
      </div>
    );
  }

  const activeTabDef = tabs.find(t => t.id === activeTab) ?? tabs[0];
  const kicker = commandReplay ? 'MATCH DAY' : commandReplayLoading ? 'MATCH DAY' : tabKickers[activeTab];
  const headerTitle = commandReplay ? 'Match Replay' : commandReplayLoading ? 'Loading Replay…' : activeTabDef.label;

  return (
    <div className="dm-app-shell flex" style={{ minHeight: '100vh' }}>
      {/* Left Navigation Rail */}
      <aside className="dm-left-nav">
        <div className="dm-left-nav-logo">
          <p className="dm-kicker">Dodgeball Manager</p>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0 }}>2026</p>
        </div>
        <nav style={{ padding: '0.5rem 0', flex: 1 }} aria-label="Primary">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`dm-nav-item ${activeTab === tab.id && !commandReplay && !commandReplayLoading ? 'dm-nav-item-active' : ''}`}
              onClick={() => { setCommandReplay(null); setActiveTab(tab.id); }}
            >
              <span className="dm-nav-dot" />
              {tab.label}
            </button>
          ))}
        </nav>
        <div style={{ padding: '0.75rem', borderTop: '1px solid #1e293b' }}>
          {menuButton}
        </div>
      </aside>

      {/* Main workspace */}
      <div className="dm-workspace">
        {/* Broadcast header */}
        <header className="dm-broadcast-header">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
            <div>
              <p className="dm-kicker">{kicker}</p>
              <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0 }}>
                {headerTitle}
              </h1>
            </div>
            <div className="dm-data" style={{ fontSize: '0.75rem', color: '#64748b' }}>
              V5 Command Center
            </div>
          </div>
        </header>

        {/* Screen content */}
        <div className="dm-content">
          {commandReplay && (
            <MatchReplay
              data={commandReplay}
              onContinue={() => setCommandReplay(null)}
            />
          )}
          {!commandReplay && commandReplayLoading && (
            <p className="dm-kicker" style={{ padding: '2rem', fontSize: '0.875rem' }}>Loading replay…</p>
          )}
          {!commandReplay && !commandReplayLoading && activeTab === 'command' && <CommandCenter onOpenReplay={openCommandReplay} />}
          {!commandReplay && !commandReplayLoading && activeTab === 'hub' && <Hub />}
          {!commandReplay && !commandReplayLoading && activeTab === 'dynasty' && <DynastyOffice />}
          {!commandReplay && !commandReplayLoading && activeTab === 'roster' && <Roster />}
          {!commandReplay && !commandReplayLoading && activeTab === 'tactics' && <Tactics />}
          {!commandReplay && !commandReplayLoading && activeTab === 'standings' && <Standings />}
          {!commandReplay && !commandReplayLoading && activeTab === 'schedule' && <Schedule />}
          {!commandReplay && !commandReplayLoading && activeTab === 'news' && <NewsWire />}
        </div>
      </div>
    </div>
  );
}

export default App;

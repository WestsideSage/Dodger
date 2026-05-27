import { useEffect, useState } from 'react';
import { MatchWeek } from './components/MatchWeek';
import { DynastyOffice } from './components/DynastyOffice';
import { Standings } from './components/LeagueContext';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
import MatchReplay from './components/MatchReplay';
import type { CommandCenterSimResponse, MatchReplayResponse } from './types';
import { careerApi, commandApi } from './api/client';

type Screen = 'loading' | 'menu' | 'game' | 'offseason';
type Tab = 'command' | 'dynasty' | 'roster' | 'standings';

const OFFSEASON_STATES = new Set([
  'season_complete_offseason_beat',
  'season_complete_recruitment_pending',
  'next_season_ready',
]);

const tabs: Array<{ id: Tab; label: string; short: string; icon?: string }> = [
  { id: 'command', label: 'Command Center', short: 'Week', icon: '*' },
  { id: 'roster', label: 'Roster', short: 'Team', icon: 'users' },
  { id: 'dynasty', label: 'Dynasty Office', short: 'Program', icon: 'briefcase' },
  { id: 'standings', label: 'Standings', short: 'Table', icon: 'list' },
];

const tabKickers: Record<string, string> = {
  command: 'WAR ROOM',
  dynasty: 'FRONT OFFICE',
  roster: 'ROSTER LAB',
  standings: 'LEAGUE OFFICE',
};

function tabFromUrl(): Tab {
  const tab = new URLSearchParams(window.location.search).get('tab');
  return tabs.some(item => item.id === tab) ? tab as Tab : 'command';
}

function App() {
  const [screen, setScreen] = useState<Screen>('loading');
  const [activeTab, setActiveTab] = useState<Tab>(tabFromUrl);
  const [postSimThisSession, setPostSimThisSession] = useState(false);
  const [postSimResult, setPostSimResult] = useState<CommandCenterSimResponse | null>(null);
  const [commandReplay, setCommandReplay] = useState<MatchReplayResponse | null>(null);
  const [commandReplayLoading, setCommandReplayLoading] = useState(false);
  const [seasonYear, setSeasonYear] = useState<number | null>(null);
  const [seasonNumber, setSeasonNumber] = useState<number | null>(null);
  const [currentWeek, setCurrentWeek] = useState<number | null>(null);

  useEffect(() => {
    const refreshCareerContext = () => {
      return careerApi.status().then((status) => {
        const state = status?.state?.state ?? '';
        setSeasonYear(status?.context?.season_year ?? null);
        setSeasonNumber(status?.state?.season_number ?? null);
        setCurrentWeek(status?.state?.week ?? null);
        setScreen(OFFSEASON_STATES.has(state) ? 'offseason' : 'game');
      });
    };

    careerApi.saveState()
      .then((data) => {
        if (!data.loaded) { setScreen('menu'); return; }
        return refreshCareerContext();
      })
      .catch(() => setScreen('menu'));
  }, []);

  useEffect(() => {
    if (screen !== 'game' && screen !== 'offseason') return;
    const params = new URLSearchParams(window.location.search);
    params.set('tab', activeTab);
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
  }, [activeTab, screen]);

  const openCommandReplay = (matchId: string) => {
    setCommandReplayLoading(true);
    commandApi.replay(matchId)
      .then(setCommandReplay)
      .finally(() => setCommandReplayLoading(false));
  };

  if (screen === 'loading') {
    return (
      <div className="app-shell" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p className="dm-kicker" style={{ fontSize: '0.875rem', letterSpacing: '0.2em' }}>Loading...</p>
      </div>
    );
  }

  if (screen === 'menu') {
    return <SaveMenu onSaveLoaded={() => window.location.reload()} />;
  }

  const menuButton = (
    <button
      className="nav-item"
      aria-label="Back to save menu"
      onClick={() => {
        careerApi.unloadSave()
          .finally(() => window.location.reload());
      }}
      title="Back to Save Menu"
    >
      <span className="dot" />
      Menu
    </button>
  );

  // During offseason the active tab follows the user's selection so they
  // can peek Roster/Standings/Dynasty before starting the next season.
  const effectiveActiveTab: Tab = activeTab;

  const activeTabDef = tabs.find(t => t.id === effectiveActiveTab) ?? tabs[0];
  const kicker = commandReplay ? 'MATCH DAY' : commandReplayLoading ? 'MATCH DAY' : tabKickers[effectiveActiveTab];
  const headerTitle = commandReplay ? 'Match Replay' : commandReplayLoading ? 'Loading Replay...' : activeTabDef.label;
  const displayedWeek = postSimResult?.dashboard?.week ?? currentWeek ?? 1;

  return (
    <div className="app-shell flex" style={{ minHeight: '100vh' }}>
      {/* Left Navigation Rail */}
      <aside className="left-nav">
        <div className="left-nav-logo">
          <p className="dm-kicker" style={{ fontSize: '0.62rem' }}>Dodgeball Manager</p>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: '2px 0 0' }}>{seasonYear ?? ''}</p>
        </div>
        <nav className="left-nav-items" aria-label="Primary">
          {tabs.map(tab => {
            // During offseason ceremonies let the player peek at read-only
            // tabs (Roster, Standings, Dynasty Office) before committing to
            // start the next season. Command Center is the ceremony surface
            // itself and stays selected.
            const isAvailable = true;
            const isActive = effectiveActiveTab === tab.id && !commandReplay && !commandReplayLoading;
            return (
              <button
                key={tab.id}
                className={`nav-item ${isActive ? 'active' : ''}`}
                aria-label={tab.label}
                aria-disabled={!isAvailable}
                title={isAvailable ? tab.label : `${tab.label} — locked during offseason`}
                onClick={() => {
                  if (isAvailable) {
                    setCommandReplay(null);
                    setActiveTab(tab.id);
                  }
                }}
                style={{ opacity: isAvailable ? 1 : 0.35, cursor: isAvailable ? 'pointer' : 'not-allowed', pointerEvents: 'auto' }}
              >
                <span className="dot" />
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className="left-nav-footer">
          <button
            className="nav-item"
            disabled
            title="Settings are coming soon"
            style={{ opacity: 0.35, cursor: 'not-allowed' }}
            onClick={() => {}}
          >
            <span className="dot" />
            Settings
          </button>
          {menuButton}
        </div>
      </aside>

      {/* Main workspace */}
      <div className="workspace">
        {/* Broadcast header */}
        <header className="broadcast-header">
          <div>
            <span className="dm-kicker">{kicker}</span>
            <h1>{headerTitle}</h1>
          </div>
          <span className="meta">Season {seasonNumber ?? seasonYear ?? '1'} -- Week {String(displayedWeek).padStart(2, '0')}</span>
        </header>

        {/* Screen content */}
        <div className="content-area">
          {commandReplay && (
            <MatchReplay
              key={commandReplay.match_id}
              data={commandReplay}
              onContinue={() => setCommandReplay(null)}
            />
          )}
          {!commandReplay && commandReplayLoading && (
            <p className="dm-kicker" style={{ padding: '2rem', fontSize: '0.875rem' }}>Loading replay...</p>
          )}
          {!commandReplay && !commandReplayLoading && effectiveActiveTab === 'command' && (
            <MatchWeek
              onOpenReplay={openCommandReplay}
              persistedResult={postSimResult}
              mode={
                screen === 'offseason' ? 'offseason'
                : postSimThisSession ? 'post-sim'
                : 'pre-sim'
              }
              onSimComplete={(payload) => {
                setPostSimResult(payload);
                setPostSimThisSession(true);
                setCurrentWeek(payload.dashboard.week);
              }}
              onAdvanceWeek={() => {
                const nextState = postSimResult?.next_state ?? '';
                setPostSimResult(null);
                setPostSimThisSession(false);
                careerApi.status().then(status => {
                  setSeasonYear(status?.context?.season_year ?? null);
                  setSeasonNumber(status?.state?.season_number ?? null);
                  setCurrentWeek(status?.state?.week ?? null);
                  if (OFFSEASON_STATES.has(nextState)) {
                    setScreen('offseason');
                  }
                }).catch(() => {});
              }}
            />
          )}
          {!commandReplay && !commandReplayLoading && effectiveActiveTab === 'dynasty' && <DynastyOffice />}
          {!commandReplay && !commandReplayLoading && effectiveActiveTab === 'roster' && <Roster />}
          {!commandReplay && !commandReplayLoading && effectiveActiveTab === 'standings' && <Standings />}
        </div>
      </div>
    </div>
  );
}

export default App;

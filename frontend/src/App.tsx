import { useEffect, useRef, useState } from 'react';
import { MatchWeek } from './components/MatchWeek';
import { DynastyOffice } from './components/DynastyOffice';
import { Standings } from './components/LeagueContext';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
import MatchReplay from './components/MatchReplay';
import type { CommandCenterSimResponse, MatchReplayResponse } from './types';
import { careerApi, commandApi } from './api/client';
import { NAV_RAIL_ATTR } from './components/shell/appContracts';
import styles from './App.module.css';

type Screen = 'loading' | 'menu' | 'game' | 'offseason';
type Tab = 'command' | 'dynasty' | 'roster' | 'standings';

const OFFSEASON_STATES = new Set([
  'season_complete_offseason_beat',
  'season_complete_recruitment_pending',
  'next_season_ready',
]);

/** Single source of truth for screen classification (#82 live-state-trust). */
// eslint-disable-next-line react-refresh/only-export-components
export function classifyScreen(state: string): 'game' | 'offseason' {
  return OFFSEASON_STATES.has(state) ? 'offseason' : 'game';
}

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

// Owner decision (planning-report.md §6 #1): hide Settings until it has real purpose.
// Flip to `true` to re-enable the nav item with zero further changes.
const SHOW_SETTINGS_NAV = false;

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
  const [offseasonBeatName, setOffseasonBeatName] = useState<string | null>(null);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const refreshCareerContext = () => {
      return careerApi.status().then((status) => {
        const state = status?.state?.state ?? '';
        setSeasonYear(status?.context?.season_year ?? null);
        setSeasonNumber(status?.state?.season_number ?? null);
        setCurrentWeek(status?.state?.week ?? null);
        setScreen(classifyScreen(state));
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
      <div className={styles.bootShell}>
        <div className={styles.boot} role="status" aria-label="Loading Dodgeball Manager">
          <p className={styles.bootKicker}>Dynasty Simulator</p>
          <p className={styles.bootBrand}>Dodgeball <em>Manager</em></p>
          <div className={styles.courtPulse} aria-hidden="true" />
        </div>
      </div>
    );
  }

  if (screen === 'menu') {
    return <SaveMenu onSaveLoaded={() => window.location.reload()} />;
  }

  const menuButton = (
    <button
      className={styles.navItem}
      aria-label="Back to save menu"
      tabIndex={navCollapsed ? -1 : 0}
      onClick={() => {
        careerApi.unloadSave()
          .finally(() => window.location.reload());
      }}
      title="Back to Save Menu"
    >
      <span className={styles.dot} />
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
    <div className={styles.shell}>
      {/* Left Navigation Rail */}
      <aside
        className={`${styles.nav}${navCollapsed ? ` ${styles.navCollapsed}` : ''}`}
        {...{ [NAV_RAIL_ATTR]: '' }}
      >
        {/* Hamburger toggle — always visible and keyboard-focusable */}
        <button
          ref={hamburgerRef}
          type="button"
          aria-expanded={!navCollapsed}
          aria-controls="primary-nav"
          aria-label="Toggle navigation"
          onClick={() => {
            setNavCollapsed((v) => !v);
            // Return focus to the hamburger after toggle so keyboard users stay oriented.
            requestAnimationFrame(() => hamburgerRef.current?.focus());
          }}
          className={styles.hamburger}
          title={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}
        >
          {/* Three-line hamburger icon drawn with box-shadow — no SVG dep */}
          <span
            aria-hidden="true"
            className={styles.hamburgerIcon}
          />
        </button>
        <div
          className={styles.navLogo}
          style={{ display: navCollapsed ? 'none' : undefined }}
        >
          <p className={`dm-kicker ${styles.navLogoLabel}`}>Dodgeball Manager</p>
          <p className={styles.navLogoYear}>{seasonYear ?? ''}</p>
        </div>
        <nav
          id="primary-nav"
          className={styles.navItems}
          aria-label="Primary"
          style={{ display: navCollapsed ? 'none' : undefined }}
        >
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
                className={`${styles.navItem}${isActive ? ` ${styles.navItemActive}` : ''}`}
                aria-label={tab.label}
                aria-disabled={!isAvailable}
                tabIndex={navCollapsed ? -1 : 0}
                title={isAvailable ? tab.label : `${tab.label} — locked during offseason`}
                onClick={() => {
                  if (isAvailable) {
                    setCommandReplay(null);
                    setActiveTab(tab.id);
                  }
                }}
                style={{ opacity: isAvailable ? 1 : 0.35, cursor: isAvailable ? 'pointer' : 'not-allowed', pointerEvents: 'auto' }}
              >
                <span className={styles.dot} />
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className={styles.navFooter}>
          {!navCollapsed && SHOW_SETTINGS_NAV && (
            <button
              className={styles.navItem}
              disabled
              title="Settings are coming soon"
              style={{ opacity: 0.35, cursor: 'not-allowed' }}
              onClick={() => {}}
            >
              <span className={styles.dot} />
              Settings
            </button>
          )}
          {!navCollapsed && menuButton}
        </div>
      </aside>

      {/* Main workspace */}
      <div className={styles.workspace}>
        {/* Broadcast header */}
        <header className={styles.header}>
          <div>
            <span className={`dm-kicker ${styles.headerKicker}`}>{kicker}</span>
            <h1 className={styles.headerTitle}>{headerTitle}</h1>
          </div>
          <span className={styles.headerMeta}>
            {screen === 'offseason'
              ? `Season ${seasonNumber ?? seasonYear ?? '1'} -- Offseason${offseasonBeatName ? ` (${offseasonBeatName})` : ''}`
              : `Season ${seasonNumber ?? seasonYear ?? '1'} -- Week ${displayedWeek}`}
          </span>
        </header>

        {/* Screen content */}
        <div className={styles.content}>
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
              onOffseasonBeatChange={setOffseasonBeatName}
              persistedResult={postSimResult}
              mode={
                screen === 'offseason' ? 'offseason'
                : postSimThisSession ? 'post-sim'
                : 'pre-sim'
              }
              onPlanWeek={setCurrentWeek}
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
                  // Trust the live career state as the authoritative router.
                  // postSimResult.next_state only exists after a manual sim; a
                  // Fast-forward advances straight to the offseason beat without
                  // populating it, so relying on nextState alone strands the
                  // player on the stale "Season complete" command-center shell.
                  const liveState = status?.state?.state ?? '';
                  setSeasonYear(status?.context?.season_year ?? null);
                  setSeasonNumber(status?.state?.season_number ?? null);
                  setCurrentWeek(status?.state?.week ?? null);
                  if (classifyScreen(nextState) === 'offseason' || classifyScreen(liveState) === 'offseason') {
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

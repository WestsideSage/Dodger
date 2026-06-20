import { useCallback, useEffect, useMemo, useState } from 'react';
import type React from 'react';
import type { SaveInfo, SaveListResponse, ClubOption } from '../types';
import { IdentityStep } from './new-game/IdentityStep';
import { CoachStep } from './new-game/CoachStep';
import { StaffHiringStep } from './new-game/StaffHiringStep';
import { StartingRecruitmentStep } from './new-game/StartingRecruitmentStep';
import { saveApi } from '../api/client';
import { RadioGroup } from './ui';
import styles from './SaveMenu.module.css';

const DEBUG_PREFIXES = ['qa-playthrough-', 'debug-', 'playtest-', 'ux-teardown-', 'test_', 'e2e-', 'e2e_', 'codex', 'command-aftermath'];

function isDebugSaveName(name: string) {
  return DEBUG_PREFIXES.some(prefix => name.startsWith(prefix));
}

// A fresh creation seed per wizard run — non-deterministic ON PURPOSE (this is
// the one place randomness is allowed: choosing which deterministic universe a
// new career lives in).
function freshCreationSeed(): number {
  return Math.floor(Math.random() * 2_147_483_646) + 1;
}

// Deterministic club monogram for save rows — initials + a stable accent
// drawn from the club name so each career reads as a distinct program.
// Presentation only; no payload fields are invented.
const MONOGRAM_PALETTE = ['#22d3ee', '#f97316', '#10b981', '#f59e0b', '#a78bfa', '#f43f5e', '#38bdf8', '#fb923c'];

function clubMonogram(name?: string | null): { initials: string; hue: string } {
  const clean = (name ?? '').trim();
  if (!clean) return { initials: '?', hue: '#475569' };
  const words = clean.split(/\s+/).filter(Boolean);
  const initials = (
    words.length >= 2 ? `${words[0][0]}${words[words.length - 1][0]}` : clean.slice(0, 2)
  ).toUpperCase();
  let hash = 0;
  for (let i = 0; i < clean.length; i += 1) hash = (hash * 31 + clean.charCodeAt(i)) | 0;
  return { initials, hue: MONOGRAM_PALETTE[Math.abs(hash) % MONOGRAM_PALETTE.length] };
}

function formatTimeAgo(timestamp?: number): string {
  if (!timestamp) return '';
  const seconds = Math.floor((Date.now() - timestamp * 1000) / 1000);
  if (seconds < 0) return 'just now';
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// Player-facing ruleset copy. FAITHFULNESS-FIRST (ADR 0002): every claim here
// must be backed by what the engine actually models — see
// src/dodgeball_sim/rulesets.py and official_scoring.py. There is NO
// velocity / sting / damage / tempo model, so the copy does not claim one.
//
// Single-ruleset standardization (owner decision 2026-06-10): every new
// career plays under the foam-official ruleset. The No-Sting/Cloth/Generic
// picker was removed from career creation — the divisions differ mainly by
// real-world ball material, a distinction a player can't feel in a sim, and
// the choice was newbie-hostile. The other ruleset profiles remain fully
// engine-supported (conformance ledger, tests, legacy saves) — depth kept,
// decision removed. Title reuses the canonical `full` form from
// `frontend/src/legibility/rulesetNames.ts` (WT-5).
// Glance list + expandable full breakdown (owner 2026-06-10: nobody reads a
// giant paragraph — key rules at a glance, everything else behind a click).
// Numbers verified against rulesets.py FOAM_OPEN (6 balls, burden majority 4,
// 5s throw clock, 180s game clock) and official_engine.run_autonomous_match
// (24-minute match window; 30 in semifinals, 40 in the final).
const standardRuleset = {
  title: "USA Dodgeball 2026.1 — Foam",
  tagline: "Six balls. Real catches. Three-minute games. Modeled on the official foam rulebook.",
  keyRules: [
    { label: "6v6 · SIX BALLS", text: "Each side fields six players and starts with three balls. Hit someone with a throw — they're out." },
    { label: "CATCHES FLIP GAMES", text: "Catch a throw and the thrower is OUT — and one of your eliminated teammates runs back on." },
    { label: "WIPE-OUT TO SCORE", text: "A game point is earned ONLY by eliminating all six opponents. No wipe-out, no point." },
    { label: "3-MINUTE LINE", text: "Held balls block throws in regulation. Past 3:00 that protection is stripped — No Blocking, sudden death until someone wins." },
    { label: "SHOT-CLOCK PRESSURE", text: "Hold most of the balls (4 of 6) and you must attack within 5 seconds or the refs make the call." },
    { label: "MANY GAMES, ONE MATCH", text: "Games run back-to-back inside a 24-minute match window. Most game points wins — draws are real." },
  ],
  fullBreakdown: [
    {
      heading: "The court and the rush",
      body: "Six starters per side from a roster of up to twelve. Six foam balls are in play — three per side — and every game opens with a rush for them. Your weekly tactics decide how hard your club commits to that rush and where it aims.",
    },
    {
      heading: "Getting players out",
      body: "A live throw that hits an opponent eliminates them. Targets can dodge, block with a held ball (in regulation), or catch. A clean catch is the biggest swing in the sport: the thrower is eliminated AND one of your eliminated teammates re-enters from the catch queue.",
    },
    {
      heading: "Scoring and the clocks",
      body: "A game point is earned only by fully eliminating the opposing six. Each game has a 3-minute regulation window; once it passes the three-minute line, No Blocking is enforced — held balls no longer block throws, and the game runs until someone closes it out. Games repeat inside the match window (24 minutes in the regular season, 30 in semifinals, 40 in the final). Most game points at full time wins the match — draws are a real result.",
    },
    {
      heading: "The burden rule",
      body: "Hold the ball majority (4 of the 6) and your side is on the clock: attack within 5 seconds or the officials make the call. Every call in a match replay carries its USA Dodgeball rulebook reference, so you can always see exactly which rule fired.",
    },
    {
      heading: "What's honestly modeled",
      body: "The sim is a deterministic abstraction of the official USA Dodgeball 2026.1 foam rules: ball counts, the catch rule, burden and throw clocks, No Blocking, and per-game set scoring are all enforced. Ball material, throw velocity, and sting are real-world distinctions the sim does not separately model — and the game never pretends otherwise.",
    },
  ],
};

interface SaveMenuProps {
  onSaveLoaded: () => void;
}

type View = 'list' | 'new' | 'takeover' | 'build_identity' | 'build_coach' | 'build_staff' | 'build_roster';

export function SaveMenu({ onSaveLoaded }: SaveMenuProps) {
  const [view, setView] = useState<View>('list');
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const isDebugQueryPresent = useMemo(() => window.location.search.includes('debug=true'), []);
  const [showDebugSaves, setShowDebugSaves] = useState(false);
  const [showIncompatibleSaves, setShowIncompatibleSaves] = useState(false);
  const baseVisible = useMemo(
    () => (showDebugSaves && isDebugQueryPresent) ? saves : saves.filter(save => !isDebugSaveName(save.name)),
    [saves, showDebugSaves, isDebugQueryPresent],
  );
  const visibleSaves = useMemo(
    () => showIncompatibleSaves ? baseVisible : baseVisible.filter(save => !save.incompatible),
    [baseVisible, showIncompatibleSaves],
  );
  const hiddenIncompatibleCount = useMemo(
    () => baseVisible.filter(save => save.incompatible).length,
    [baseVisible],
  );
  const hiddenDebugCount = useMemo(
    () => isDebugQueryPresent ? saves.filter(save => isDebugSaveName(save.name)).length : 0,
    [saves, isDebugQueryPresent],
  );
  const continueSave = useMemo(() => {
    return saves.find(save => !save.incompatible && !isDebugSaveName(save.name));
  }, [saves]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [clubs, setClubs] = useState<ClubOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New save form state
  const [newName, setNewName] = useState('');
  const [newClubId, setNewClubId] = useState('aurora');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  // Build from scratch state
  const [buildIdentity, setBuildIdentity] = useState({ save_name: '', club_name: '', city: '', colors: '#22d3ee,#1e293b' });
  const [buildCoach, setBuildCoach] = useState({ coach_name: '', coach_backstory: 'Tactical Mastermind' });
  // V22 Phase 1: per-creation seed. It drives the founding prospect pool the
  // wizard SHOWS (?seed= on starting-prospects) and the career the build POST
  // creates (root_seed) — both must be the same number, held here.
  const [buildSeed, setBuildSeed] = useState<number>(() => freshCreationSeed());
  // V22 Phase 3: the wizard's founding staff picks (department -> candidate).
  const [buildStaff, setBuildStaff] = useState<Record<string, string>>({});

  const [deleting, setDeleting] = useState<string | null>(null);

  const loadSaveList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: SaveListResponse = await saveApi.list();
      setSaves(data.saves);
      setActivePath(data.active_path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load saves');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadClubs = useCallback(async () => {
    try {
      const data = await saveApi.clubs();
      setClubs(data.clubs);
      if (data.clubs.length > 0) setNewClubId(data.clubs[0].club_id);
    } catch {
      // clubs list is optional; new-game form still works with default
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => {
      void loadSaveList();
      void loadClubs();
    });
  }, [loadClubs, loadSaveList]);

  async function handleLoad(path: string) {
    setError(null);
    try {
      await saveApi.load(path);
      onSaveLoaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load save');
    }
  }

  async function handleDelete(path: string) {
    if (!confirm('Delete this save? This cannot be undone.')) return;
    setDeleting(path);
    setError(null);
    try {
      await saveApi.delete(path);
      await loadSaveList();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete save');
    } finally {
      setDeleting(null);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) {
      setCreateError('Save name is required');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      await saveApi.create({
        name: newName.trim(),
        club_id: newClubId,
        // Single-ruleset standardization: every new career is foam-official.
        ruleset_selection: 'official_foam',
      });
      onSaveLoaded();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create save');
      setCreating(false);
    }
  }

  async function handleBuildFromScratch(rosterIds: string[]) {
    setCreating(true);
    setCreateError(null);
    try {
      await saveApi.buildFromScratch({
        save_name: buildIdentity.save_name,
        club_name: buildIdentity.club_name,
        city: buildIdentity.city,
        colors: buildIdentity.colors,
        coach_name: buildCoach.coach_name,
        coach_backstory: buildCoach.coach_backstory,
        roster_player_ids: rosterIds,
        // V22 Phase 3: the founding staff hired in the wizard's budget step.
        // Omitted when empty (a failed market fetch keeps the step blocked,
        // but never let {} reach the backend's all-six validation).
        ...(Object.keys(buildStaff).length > 0 ? { staff_choices: buildStaff } : {}),
        // V22 Phase 1: the same seed the prospect list was fetched with.
        root_seed: buildSeed,
        // Single-ruleset standardization: every new career is foam-official.
        ruleset_selection: 'official_foam',
      });
      onSaveLoaded();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create custom save');
      setCreating(false);
    }
  }

  return (
    <div
      data-testid="save-menu"
      className={styles.shell}
    >
      <div className={styles.card}>
        {/* Title block */}
        <div className={styles.brand}>
          <p className={styles.brandKicker}>Dynasty simulator</p>
          <h1 className={styles.brandTitle}>
            Dodgeball <em>Manager</em>
          </h1>
          <p className={styles.brandTagline}>Run the program. Read the league. Own the result.</p>
        </div>

        {/* Main panel */}
        <div className={`dm-panel ${styles.panel}`}>
          {/* Tab bar */}
          <div className={styles.tabs}>
            <button
              onClick={() => setView('list')}
              className={`${styles.tab}${view === 'list' ? ` ${styles.tabActive}` : ''}`}
            >
              Load Game
            </button>
            <button
              onClick={() => setView('new')}
              data-testid="new-game-tab"
              className={`${styles.tab}${view === 'new' ? ` ${styles.tabActive}` : ''}`}
            >
              New Game
            </button>
          </div>

          <div className={styles.panelBody}>
            {error && (
              <div className={styles.errorBanner}>
                {error}
              </div>
            )}

            {view === 'list' && (
              <div data-testid="save-list">
                {!loading && hiddenDebugCount > 0 && !showDebugSaves && (
                  <div className={styles.debugBar}>
                    <span className={styles.debugLabel}>
                      {hiddenDebugCount} debug save{hiddenDebugCount !== 1 ? 's' : ''} hidden ·{' '}
                      <button
                        onClick={() => setShowDebugSaves(true)}
                        className={styles.debugToggle}
                      >
                        Show
                      </button>
                    </span>
                  </div>
                )}
                {!loading && showDebugSaves && hiddenDebugCount > 0 && (
                  <div className={styles.debugBar}>
                    <button
                      onClick={() => setShowDebugSaves(false)}
                      className={styles.debugToggle}
                    >
                      Hide debug saves
                    </button>
                  </div>
                )}
                {loading ? (
                  <p className={styles.loadingText}>
                    Loading saves…
                  </p>
                ) : visibleSaves.length === 0 ? (
                  <div className={styles.emptyState}>
                    <p className={styles.emptyText}>No saves found.</p>
                    <button
                      onClick={() => setView('new')}
                      className={styles.startNewBtn}
                    >
                      Start New Game
                    </button>
                  </div>
                ) : (
                  <div>
                    {continueSave && (
                      <div
                        data-testid="continue-career-hero"
                        className={styles.hero}
                      >
                        <div className={styles.heroInfo}>
                          <p className={styles.heroEyebrow}>
                            Continue Active Career
                          </p>
                          <h3 className={styles.heroName}>
                            {continueSave.name}
                          </h3>
                          <p className={styles.heroMeta}>
                            {continueSave.club_name ?? 'Unknown Club'} · Season {continueSave.season_number ?? 1} · Week {continueSave.week ?? 1}
                          </p>
                          {continueSave.wins !== undefined && (
                            <p className={styles.heroRecord}>
                              Record: {continueSave.wins}-{continueSave.losses}-{continueSave.draws} · saved {formatTimeAgo(continueSave.last_modified)}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => handleLoad(continueSave.path)}
                          className="dm-action dm-action-primary"
                        >
                          Continue
                        </button>
                      </div>
                    )}
                    <ul className={styles.rowList}>
                    {visibleSaves.map((save) => {
                      const monogram = clubMonogram(save.club_name ?? save.club_id);
                      return (
                      <li
                        key={save.path}
                        data-testid="save-item"
                        className={styles.row}
                        style={{ opacity: activePath === save.path ? 1 : 0.92 }}
                      >
                        <span
                          className={`${styles.monogram}${save.incompatible ? ` ${styles.monogramIncompatible}` : ''}`}
                          style={{ '--mono-hue': monogram.hue } as React.CSSProperties}
                          aria-hidden="true"
                        >
                          {monogram.initials}
                        </span>
                        <div className={styles.rowBody}>
                          <div className={styles.rowName}>
                            {save.name}
                            {activePath === save.path && (
                              <span className={styles.rowActiveBadge}>
                                active
                              </span>
                            )}
                            {save.incompatible && (
                              <span className={styles.rowIncompatibleBadge}>
                                Incompatible
                              </span>
                            )}
                          </div>
                          <div className={styles.rowMeta}>
                            {save.incompatible ? (
                              <span className={styles.rowIncompatibleNote}>
                                Save file incompatible — start a new career.
                              </span>
                            ) : (
                              <div className={styles.rowMetaFlex}>
                                <span className={styles.rowMetaClub}>
                                  {save.club_name ?? save.club_id ?? 'Unknown club'}
                                </span>
                                <span className={styles.rowMetaDot}>·</span>
                                <span>Season {save.season_number ?? 1}</span>
                                <span className={styles.rowMetaDot}>·</span>
                                <span>Week {save.week ?? 1}</span>
                                {save.wins !== undefined && (
                                  <>
                                    <span className={styles.rowMetaDot}>·</span>
                                    <span className={styles.rowRecord}>
                                      {save.wins}-{save.losses}-{save.draws}
                                    </span>
                                  </>
                                )}
                                {save.last_modified !== undefined && (
                                  <>
                                    <span className={styles.rowMetaDot}>·</span>
                                    <span className={styles.rowModified}>
                                      saved {formatTimeAgo(save.last_modified)}
                                    </span>
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => handleLoad(save.path)}
                          disabled={activePath === save.path || save.incompatible}
                          data-testid="load-save-btn"
                          className="dm-action dm-action-secondary"
                        >
                          {activePath === save.path ? 'Loaded' : 'Load'}
                        </button>
                        {save.path !== 'dodgeball_sim.db' && (
                          <button
                            onClick={() => handleDelete(save.path)}
                            disabled={deleting === save.path}
                            data-testid="delete-save-btn"
                            className="dm-action dm-action-danger"
                          >
                            {deleting === save.path ? '…' : 'Delete'}
                          </button>
                        )}
                      </li>
                      );
                    })}
                  </ul>
                  {hiddenIncompatibleCount > 0 && (
                    <button
                      type="button"
                      onClick={() => setShowIncompatibleSaves(v => !v)}
                      data-testid="toggle-incompatible"
                      className={styles.archiveToggle}
                    >
                      {showIncompatibleSaves
                        ? `Hide archive (${hiddenIncompatibleCount} incompatible)`
                        : `Show archive (${hiddenIncompatibleCount} incompatible)`}
                    </button>
                  )}
                  </div>
                )}
              </div>
            )}

            {view === 'new' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {/* How it plays — single standard ruleset (no picker; owner
                    decision 2026-06-10: foam-official is the one way to play) */}
                <div style={{ background: '#0b1329', border: '1px solid #1e293b', borderRadius: '8px', padding: '1.25rem' }} data-testid="ruleset-standard-card">
                  <span style={{
                    display: 'block',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.5rem',
                    fontWeight: 700,
                  }}>
                    How It Plays
                  </span>
                  <div style={{
                    background: 'rgba(34, 211, 238, 0.04)',
                    borderLeft: '3px solid #22d3ee',
                    padding: '0.75rem 1rem',
                    borderRadius: '0 4px 4px 0',
                  }}>
                    <h4 style={{ margin: '0 0 0.2rem 0', fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc' }}>
                      {standardRuleset.title}
                    </h4>
                    <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.75rem', color: '#22d3ee', fontWeight: 600 }}>
                      {standardRuleset.tagline}
                    </p>
                    {/* Key rules at a glance — short label + one-liner per row. */}
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.45rem' }} data-testid="ruleset-key-rules">
                      {standardRuleset.keyRules.map((rule) => (
                        <li key={rule.label} style={{ display: 'flex', gap: '0.6rem', alignItems: 'baseline' }}>
                          <span style={{
                            flex: '0 0 9.5rem',
                            fontSize: '0.62rem',
                            fontFamily: 'var(--font-display)',
                            fontWeight: 800,
                            letterSpacing: '0.06em',
                            color: '#22d3ee',
                            whiteSpace: 'nowrap',
                          }}>
                            {rule.label}
                          </span>
                          <span style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.4 }}>
                            {rule.text}
                          </span>
                        </li>
                      ))}
                    </ul>
                    {/* The deep dive, for the players who DO want to read
                        everything — native details/summary, keyboard friendly. */}
                    <details style={{ marginTop: '0.85rem' }} data-testid="ruleset-full-breakdown">
                      <summary style={{
                        cursor: 'pointer',
                        fontSize: '0.7rem',
                        fontFamily: 'var(--font-display)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: '#64748b',
                        fontWeight: 700,
                      }}>
                        Full rulebook breakdown
                      </summary>
                      <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                        {standardRuleset.fullBreakdown.map((section) => (
                          <div key={section.heading}>
                            <h5 style={{ margin: '0 0 0.15rem 0', fontSize: '0.74rem', fontWeight: 700, color: '#e2e8f0' }}>
                              {section.heading}
                            </h5>
                            <p style={{ margin: 0, fontSize: '0.74rem', color: '#94a3b8', lineHeight: 1.5 }}>
                              {section.body}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
                  {/* Take Over a Program Button */}
                  <button
                    onClick={() => setView('takeover')}
                    style={{
                      flex: 1,
                      padding: '2rem 1.25rem',
                      background: '#0f172a',
                      border: '2px solid #f97316',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      cursor: 'pointer',
                      textAlign: 'center',
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'transform 0.15s, background 0.15s',
                    }}
                  >
                    <span style={{
                      position: 'absolute',
                      top: '-10px',
                      background: '#f97316',
                      color: '#fff',
                      fontSize: '0.625rem',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      padding: '0.2rem 0.6rem',
                      borderRadius: '20px',
                      letterSpacing: '0.05em',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    }}>
                      Faster Start
                    </span>
                    <h3 style={{ margin: '0.5rem 0 0.5rem', color: '#f97316', fontSize: '1.25rem', fontWeight: 800 }}>Take Over a Program</h3>
                    <p style={{ margin: 0, fontSize: '0.8125rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                      Inherit an established Premier League club — the top of a
                      28-club pyramid where the bottom two go down every season.
                    </p>
                  </button>

                  {/* Build from Scratch Button */}
                  <button
                    onClick={() => {
                      // V22 Phase 1: every wizard run is a new universe —
                      // fresh seed, fresh founding class, fresh staff market.
                      setBuildSeed(freshCreationSeed());
                      setBuildStaff({});
                      setView('build_identity');
                    }}
                    style={{
                      flex: 1,
                      padding: '2rem 1.25rem',
                      background: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      cursor: 'pointer',
                      textAlign: 'center',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'transform 0.15s, background 0.15s',
                    }}
                  >
                    <h3 style={{ margin: '0.5rem 0 0.5rem', color: '#22d3ee', fontSize: '1.25rem', fontWeight: 800 }}>Build from Scratch</h3>
                    <p style={{ margin: 0, fontSize: '0.8125rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                      Found a club at the bottom of the District League (D3)
                      and climb the pyramid toward WORLDS.
                    </p>
                  </button>
                </div>
              </div>
            )}

            {view === 'takeover' && (
              <form
                onSubmit={handleCreate}
                data-testid="new-game-form"
                style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
              >
                <div>
                  <label
                    htmlFor="new-save-name"
                    style={{
                    display: 'block',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.25rem',
                  }}>
                    Save Name
                  </label>
                  <input
                    id="new-save-name"
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="My Career"
                    data-testid="save-name-input"
                    style={{
                      width: '100%',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#0f172a',
                      padding: '0.5rem 0.75rem',
                      fontSize: '0.875rem',
                      color: '#e2e8f0',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <span
                    id="new-save-club-label"
                    style={{
                    display: 'block',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.25rem',
                  }}>
                    Club
                  </span>
                  {/* Honest pre-creation guidance (PT4-08): rosters are generated
                      fresh from the same templates, so the pick is identity, not a
                      head start — but every Premier club lives under the same real
                      stakes, and that includes you. */}
                  <p style={{ fontSize: '0.6875rem', color: '#64748b', margin: '0 0 0.375rem' }}>
                    Every Premier club starts with a comparable six — the choice is the identity
                    and rival history you inherit. The stakes are the same for all of them: finish
                    in the bottom two and your club really is relegated; win the league and WORLDS
                    is next.
                  </p>
                  {clubs.length > 0 ? (
                    <RadioGroup
                      value={newClubId}
                      onChange={setNewClubId}
                      labelledBy="new-save-club-label"
                      options={clubs.map((club) => ({
                        value: club.club_id,
                        label: club.tagline ? `${club.name} — ${club.tagline}` : club.name,
                        'data-testid': `club-option-${club.club_id}`,
                      }))}
                      style={{
                        listStyle: 'none',
                        padding: 0,
                        margin: 0,
                        border: '1px solid #1e293b',
                        borderRadius: '4px',
                        overflow: 'hidden',
                      }}
                      renderOption={({ option, selected, radioProps }) => {
                        const club = clubs.find((c) => c.club_id === option.value)!;
                        return (
                          <div
                            {...radioProps}
                            aria-label={option.label}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.75rem',
                              padding: '0.75rem',
                              cursor: 'pointer',
                              outline: 'none',
                              borderBottom: '1px solid #1e293b',
                              borderLeft: selected ? '2px solid #f97316' : '2px solid transparent',
                              background: selected ? 'rgba(249,115,22,0.08)' : 'transparent',
                              boxShadow: radioProps.tabIndex === 0 ? 'inset 0 0 0 1px rgba(34,211,238,0.25)' : 'none',
                              transition: 'background 0.1s',
                            }}
                          >
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>{club.name}</div>
                              {club.tagline && (
                                <div style={{ fontSize: '0.75rem', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{club.tagline}</div>
                              )}
                            </div>
                            {selected && (
                              <span aria-hidden="true" style={{ color: '#f97316', fontSize: '0.75rem' }}>✓</span>
                            )}
                          </div>
                        );
                      }}
                    />
                  ) : (
                    <select
                      aria-labelledby="new-save-club-label"
                      value={newClubId}
                      onChange={(e) => setNewClubId(e.target.value)}
                      style={{
                        width: '100%',
                        borderRadius: '4px',
                        border: '1px solid #334155',
                        background: '#0f172a',
                        padding: '0.5rem 0.75rem',
                        fontSize: '0.875rem',
                        color: '#e2e8f0',
                      }}
                    >
                      {/* Fallback only (clubs fetch failed) — names must match
                          sample_data.curated_clubs + world.RIDGELINE. */}
                      <option value="aurora">Aurora Sentinels</option>
                      <option value="lunar">Lunar Syndicate</option>
                      <option value="northwood">Northwood Ironclads</option>
                      <option value="harbor">Harbor Tidebreakers</option>
                      <option value="granite">Granite Specters</option>
                      <option value="solstice">Solstice Flare</option>
                      <option value="ridgeline">Ridgeline Vanguard</option>
                    </select>
                  )}
                </div>

                <div>
                  <span style={{
                    display: 'block',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.25rem',
                  }}>
                    Ruleset
                  </span>
                  {/* Single standard ruleset — no picker (owner decision
                      2026-06-10: every career is foam-official). */}
                  <p style={{ margin: 0, fontSize: '0.875rem', color: '#e2e8f0', fontWeight: 600 }}>
                    {standardRuleset.title}
                  </p>
                  <p style={{ fontSize: '0.6875rem', color: '#64748b', margin: '0.375rem 0 0' }}>
                    {standardRuleset.tagline}
                  </p>
                </div>

                {createError && (
                  <div
                    role="alert"
                    data-testid="new-save-error-banner"
                    style={{
                      padding: '0.75rem 1rem',
                      background: 'rgba(251,113,133,0.12)',
                      border: '1px solid #fb7185',
                      borderRadius: '4px',
                      color: '#fecdd3',
                      fontSize: '0.875rem',
                    }}
                  >
                    {createError}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button type="button" onClick={() => setView('new')} style={{ padding: '0.625rem 1.25rem', background: '#334155', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Back</button>
                  <button
                    type="submit"
                    disabled={creating}
                    data-testid="create-save-btn"
                    style={{
                      flex: 1,
                      borderRadius: '4px',
                      background: '#f97316',
                      border: '1px solid #ea6c0a',
                      padding: '0.625rem 1.25rem',
                      fontSize: '0.8125rem',
                      fontFamily: 'var(--font-display)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.075em',
                      color: '#fff',
                      cursor: creating ? 'not-allowed' : 'pointer',
                      opacity: creating ? 0.5 : 1,
                      fontWeight: 600,
                    }}
                  >
                    {creating ? 'Creating…' : 'Start Career'}
                  </button>
                </div>
              </form>
            )}

            {view === 'build_identity' && <IdentityStep identity={buildIdentity} setIdentity={setBuildIdentity} onNext={() => setView('build_coach')} onBack={() => setView('new')} takenNames={saves.map(s => s.name)} />}
            {view === 'build_coach' && <CoachStep coach={buildCoach} setCoach={setBuildCoach} onBack={() => setView('build_identity')} onNext={() => setView('build_staff')} />}
            {view === 'build_staff' && <StaffHiringStep seed={buildSeed} choices={buildStaff} setChoices={setBuildStaff} onBack={() => setView('build_coach')} onNext={() => setView('build_roster')} />}
            {view === 'build_roster' && <StartingRecruitmentStep seed={buildSeed} onCommit={handleBuildFromScratch} onBack={() => setView('build_staff')} creating={creating} />}
            {createError && view.startsWith('build_') && (
              <div
                role="alert"
                data-testid="build-commit-error-banner"
                style={{
                  marginTop: '1rem',
                  padding: '0.75rem 1rem',
                  background: 'rgba(251,113,133,0.12)',
                  border: '1px solid #fb7185',
                  borderRadius: '4px',
                  color: '#fecdd3',
                  fontSize: '0.875rem',
                }}
              >
                {createError}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

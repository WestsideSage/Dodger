import { useCallback, useEffect, useMemo, useState } from 'react';
import type React from 'react';
import type { SaveInfo, SaveListResponse, ClubOption } from '../types';
import { IdentityStep } from './new-game/IdentityStep';
import { CoachStep } from './new-game/CoachStep';
import { StartingRecruitmentStep } from './new-game/StartingRecruitmentStep';
import { saveApi } from '../api/client';
import { RadioGroup } from './ui';

const DEBUG_PREFIXES = ['qa-playthrough-', 'debug-', 'playtest-', 'ux-teardown-', 'test_', 'e2e-', 'e2e_', 'codex', 'command-aftermath'];

function isDebugSaveName(name: string) {
  return DEBUG_PREFIXES.some(prefix => name.startsWith(prefix));
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
// must be backed by what the engine actually models. The engine's
// outcome-affecting per-ruleset differences are the ball count, the burden
// majority threshold, the ball material (which changes the section-21
// ricochet-save outcome — foam saves the hit player, cloth does not), and the
// per-ruleset scoring model (foam earns a point on elimination only; cloth
// scores 2/1/0) — see src/dodgeball_sim/rulesets.py and official_scoring.py —
// plus the official catch resolution (catch outs the thrower and resurrects a
// teammate). There is NO velocity / sting / damage / tempo model, so the copy
// does not claim one.
//
// Official titles reuse the canonical `full` form from
// `frontend/src/legibility/rulesetNames.ts` (WT-5) — do not invent variants.
// `generic` keeps its friendlier non-official title (its canonical name maps to
// "Legacy survivor scoring"), and carries no USA Dodgeball lineage line.
const rulesetExplanations: Record<string, { title: string; desc: string; bullet: string }> = {
  generic: {
    title: "Classic Dodgeball Rules",
    desc: "The original Dodger simulation: survivor-based scoring with classical catching dynamics. A balanced default that is not tied to the USA Dodgeball rule set.",
    bullet: "• 6v6 Format · Survivor scoring · High comeback potential",
  },
  official_foam: {
    title: "USA Dodgeball 2026.1 — Foam",
    desc: "Officially-inspired foam division: six balls in play and the official catch rule (a catch eliminates the thrower and resurrects a teammate). A match is decided over multiple games, and a game point is earned only by fully eliminating the opponent. Modeled as a deterministic abstraction — the real-world live-officiating calls (No Blocking, throw clock) are announced for flavor but are not yet outcome-enforced.",
    bullet: "• 6v6 Format · 6 balls (3 per side) · Catch outs thrower + resurrects · 1 game point per elimination win",
  },
  official_no_sting: {
    title: "USA Dodgeball 2026.1 — No-Sting",
    desc: "Same modeled rules as the Foam division — six balls, the official catch rule, and a game point only on full elimination. The difference is the real-world ball material (low-sting); grip, possession control, and pacing are not separately simulated. Live-officiating calls (No Blocking, throw clock) are announced but not yet outcome-enforced.",
    bullet: "• 6v6 Format · 6 balls (3 per side) · Catch outs thrower + resurrects · 1 game point per elimination win",
  },
  official_cloth: {
    title: "USA Dodgeball 2026.1 — Cloth",
    desc: "Officially-inspired cloth division: five balls in play (two per side plus one neutral center), which lowers the burden majority to 3 and shifts how possession pressure builds. The official catch rule applies, and games are scored differently from foam — a win (elimination or the player majority at time expiry) is worth 2 game points, a tie 1 each. Throw velocity and hit severity are not separately modeled; this is a deterministic abstraction of the official rules.",
    bullet: "• 6v6 Format · 5 balls (2 per side + 1 center) · Lower burden threshold · Win = 2 game points, tie = 1",
  },
};

interface SaveMenuProps {
  onSaveLoaded: () => void;
}

type View = 'list' | 'new' | 'takeover' | 'build_identity' | 'build_coach' | 'build_roster';

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
  // V11: official-ruleset opt-in at career creation only.
  // Phase 4b (D4): new careers default to the foam-official ruleset (real
  // set-based scoring + the retuned, OVR-rewarding official engine). Generic
  // stays selectable; existing legacy saves are unaffected.
  const [rulesetSelection, setRulesetSelection] = useState<string>('official_foam');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  // Build from scratch state
  const [buildIdentity, setBuildIdentity] = useState({ save_name: '', club_name: '', city: '', colors: '#22d3ee,#1e293b' });
  const [buildCoach, setBuildCoach] = useState({ coach_name: '', coach_backstory: 'Tactical Mastermind' });

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
        ruleset_selection: rulesetSelection === 'generic' ? null : rulesetSelection,
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
        ruleset_selection: rulesetSelection === 'generic' ? null : rulesetSelection,
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
      className="landing-shell"
    >
      <div className="landing-card">
        {/* Title block */}
        <div className="landing-brand">
          <p className="kicker">Dynasty simulator</p>
          <h1>
            Dodgeball <em>Manager</em>
          </h1>
          <p className="tagline">Run the program. Read the league. Own the result.</p>
        </div>

        {/* Main panel */}
        <div
          className="dm-panel"
          style={{ borderRadius: '6px', overflow: 'hidden' }}
        >
          {/* Tab bar */}
          <div style={{ display: 'flex', borderBottom: '1px solid #1e293b' }}>
            <button
              onClick={() => setView('list')}
              style={{
                flex: 1,
                padding: '0.75rem',
                fontSize: '0.8125rem',
                fontFamily: 'var(--font-display)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
                borderBottom: view === 'list' ? '2px solid #f97316' : '2px solid transparent',
                color: view === 'list' ? '#f97316' : '#64748b',
                transition: 'color 0.15s',
                marginBottom: '-1px',
              }}
            >
              Load Game
            </button>
            <button
              onClick={() => setView('new')}
              data-testid="new-game-tab"
              style={{
                flex: 1,
                padding: '0.75rem',
                fontSize: '0.8125rem',
                fontFamily: 'var(--font-display)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
                borderBottom: view === 'new' ? '2px solid #f97316' : '2px solid transparent',
                color: view === 'new' ? '#f97316' : '#64748b',
                transition: 'color 0.15s',
                marginBottom: '-1px',
              }}
            >
              New Game
            </button>
          </div>

          <div style={{ padding: '1.25rem' }}>
            {error && (
              <div style={{
                marginBottom: '1rem',
                borderRadius: '4px',
                border: '1px solid rgba(244,63,94,0.4)',
                background: 'rgba(244,63,94,0.10)',
                padding: '0.75rem',
                fontSize: '0.875rem',
                color: '#fb7185',
              }}>
                {error}
              </div>
            )}

            {view === 'list' && (
              <div data-testid="save-list">
                {!loading && hiddenDebugCount > 0 && !showDebugSaves && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#475569' }}>
                      {hiddenDebugCount} debug save{hiddenDebugCount !== 1 ? 's' : ''} hidden ·{' '}
                      <button
                        onClick={() => setShowDebugSaves(true)}
                        style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 0, fontSize: '0.75rem', textDecoration: 'underline' }}
                      >
                        Show
                      </button>
                    </span>
                  </div>
                )}
                {!loading && showDebugSaves && hiddenDebugCount > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
                    <button
                      onClick={() => setShowDebugSaves(false)}
                      style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 0, fontSize: '0.75rem', textDecoration: 'underline' }}
                    >
                      Hide debug saves
                    </button>
                  </div>
                )}
                {loading ? (
                  <p style={{ padding: '1.5rem 0', textAlign: 'center', fontSize: '0.875rem', color: '#64748b' }}>
                    Loading saves…
                  </p>
                ) : visibleSaves.length === 0 ? (
                  <div style={{ padding: '2rem 0', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '1rem' }}>No saves found.</p>
                    <button
                      onClick={() => setView('new')}
                      style={{
                        borderRadius: '4px',
                        background: '#f97316',
                        border: '1px solid #ea6c0a',
                        padding: '0.5rem 1.25rem',
                        fontSize: '0.8125rem',
                        fontFamily: 'var(--font-display)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.075em',
                        color: '#020617',
                        cursor: 'pointer',
                      }}
                    >
                      Start New Game
                    </button>
                  </div>
                ) : (
                  <div>
                    {continueSave && (
                      <div
                        data-testid="continue-career-hero"
                        style={{
                          marginBottom: '1.5rem',
                          borderRadius: '6px',
                          border: '1px solid rgba(249, 115, 22, 0.3)',
                          background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.08) 0%, rgba(15, 23, 42, 0.6) 100%)',
                          padding: '1.25rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '1rem',
                          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
                        }}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{
                            fontFamily: 'var(--font-mono-data)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.15em',
                            fontSize: '0.625rem',
                            color: '#f97316',
                            margin: '0 0 0.35rem',
                          }}>
                            Continue Active Career
                          </p>
                          <h3 style={{
                            fontFamily: 'var(--font-display)',
                            fontSize: '1.25rem',
                            fontWeight: 700,
                            color: '#ffffff',
                            margin: '0 0 0.25rem',
                            letterSpacing: '0.03em',
                          }}>
                            {continueSave.name}
                          </h3>
                          <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: 0 }}>
                            {continueSave.club_name ?? 'Unknown Club'} · Season {continueSave.season_number ?? 1} · Week {continueSave.week ?? 1}
                          </p>
                          {continueSave.wins !== undefined && (
                            <p style={{ fontSize: '0.6875rem', color: '#64748b', margin: '0.25rem 0 0' }}>
                              Record: {continueSave.wins}-{continueSave.losses}-{continueSave.draws} · saved {formatTimeAgo(continueSave.last_modified)}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => handleLoad(continueSave.path)}
                          className="dm-action dm-action-primary"
                          style={{ padding: '0.625rem 1.5rem', fontSize: '0.75rem', fontWeight: 700 }}
                        >
                          Continue
                        </button>
                      </div>
                    )}
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {visibleSaves.map((save) => {
                      const monogram = clubMonogram(save.club_name ?? save.club_id);
                      return (
                      <li
                        key={save.path}
                        data-testid="save-item"
                        className="landing-save-row"
                        style={{ opacity: activePath === save.path ? 1 : 0.92 }}
                      >
                        <span
                          className={`landing-monogram${save.incompatible ? ' is-incompatible' : ''}`}
                          style={{ '--mono-hue': monogram.hue } as React.CSSProperties}
                          aria-hidden="true"
                        >
                          {monogram.initials}
                        </span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {save.name}
                            {activePath === save.path && (
                              <span style={{
                                marginLeft: '0.5rem',
                                fontSize: '0.6875rem',
                                color: '#22d3ee',
                                fontFamily: 'var(--font-display)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.1em',
                              }}>
                                active
                              </span>
                            )}
                            {save.incompatible && (
                              <span style={{
                                marginLeft: '0.5rem',
                                fontSize: '0.6875rem',
                                color: '#f43f5e',
                                fontFamily: 'var(--font-display)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.1em',
                                border: '1px solid rgba(244,63,94,0.4)',
                                padding: '0.05rem 0.25rem',
                                borderRadius: '2px',
                                background: 'rgba(244,63,94,0.1)',
                              }}>
                                Incompatible
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.125rem' }}>
                            {save.incompatible ? (
                              <span style={{ color: '#fda4af' }}>
                                Save file incompatible — start a new career.
                              </span>
                            ) : (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem 0.5rem', alignItems: 'center' }}>
                                <span style={{ color: '#94a3b8', fontWeight: 500 }}>
                                  {save.club_name ?? save.club_id ?? 'Unknown club'}
                                </span>
                                <span style={{ color: '#475569' }}>·</span>
                                <span>Season {save.season_number ?? 1}</span>
                                <span style={{ color: '#475569' }}>·</span>
                                <span>Week {save.week ?? 1}</span>
                                {save.wins !== undefined && (
                                  <>
                                    <span style={{ color: '#475569' }}>·</span>
                                    <span style={{ fontFamily: 'var(--font-mono-data)', color: '#64748b' }}>
                                      {save.wins}-{save.losses}-{save.draws}
                                    </span>
                                  </>
                                )}
                                {save.last_modified !== undefined && (
                                  <>
                                    <span style={{ color: '#475569' }}>·</span>
                                    <span style={{ color: '#475569' }}>
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
                          style={{ minHeight: '2rem', padding: '0.25rem 0.75rem', fontFamily: 'var(--font-display)' }}
                        >
                          {activePath === save.path ? 'Loaded' : 'Load'}
                        </button>
                        {save.path !== 'dodgeball_sim.db' && (
                          <button
                            onClick={() => handleDelete(save.path)}
                            disabled={deleting === save.path}
                            data-testid="delete-save-btn"
                            className="dm-action dm-action-danger"
                            style={{ minHeight: '2rem', padding: '0.25rem 0.75rem', fontFamily: 'var(--font-display)' }}
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
                      style={{
                        marginTop: '0.75rem',
                        background: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        fontSize: '0.6875rem',
                        fontFamily: 'var(--font-display)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        cursor: 'pointer',
                        padding: '0.25rem 0',
                      }}
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
                {/* Ruleset Selection Header & Selector */}
                <div style={{ background: '#0b1329', border: '1px solid #1e293b', borderRadius: '8px', padding: '1.25rem' }}>
                  <label style={{
                    display: 'block',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.5rem',
                    fontWeight: 700,
                  }}>
                    Select Career Ruleset
                  </label>
                  <select
                    value={rulesetSelection}
                    onChange={(e) => setRulesetSelection(e.target.value)}
                    data-testid="ruleset-select-new"
                    style={{
                      width: '100%',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#0f172a',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      color: '#e2e8f0',
                      outline: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    <option value="generic">Generic (Classic Dodger sim)</option>
                    <option value="official_foam">USA Dodgeball 2026.1 — Foam</option>
                    <option value="official_no_sting">USA Dodgeball 2026.1 — No-Sting</option>
                    <option value="official_cloth">USA Dodgeball 2026.1 — Cloth</option>
                  </select>

                  {/* Dynamic Explanation Card */}
                  <div style={{
                    marginTop: '1rem',
                    background: 'rgba(34, 211, 238, 0.04)',
                    borderLeft: '3px solid #22d3ee',
                    padding: '0.75rem 1rem',
                    borderRadius: '0 4px 4px 0',
                  }}>
                    <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc' }}>
                      {rulesetExplanations[rulesetSelection].title}
                    </h4>
                    <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
                      {rulesetExplanations[rulesetSelection].desc}
                    </p>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: '#22d3ee', fontWeight: 600 }}>
                      {rulesetExplanations[rulesetSelection].bullet}
                    </p>
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
                      Lead one of the 6 established league franchises to championship glory.
                    </p>
                  </button>

                  {/* Build from Scratch Button */}
                  <button
                    onClick={() => setView('build_identity')}
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
                      Create a custom club from identity to starting roster.
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
                  {/* Honest pre-creation guidance: rosters are generated fresh at
                      career start from the same templates, so there is no
                      stronger/weaker pick to reveal here — only identity. */}
                  <p style={{ fontSize: '0.6875rem', color: '#64748b', margin: '0 0 0.375rem' }}>
                    Every club starts with a comparable six — this choice is about the identity
                    and rival style you inherit, not a difficulty setting.
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
                      <option value="aurora">Aurora Pilots</option>
                      <option value="lunar">Lunar Arcs</option>
                      <option value="northwood">Northwood Wreckers</option>
                      <option value="harbor">Harbor Anchors</option>
                      <option value="granite">Granite Foxes</option>
                      <option value="solstice">Solstice Embers</option>
                    </select>
                  )}
                </div>

                <div>
                  <label
                    htmlFor="new-save-ruleset"
                    style={{
                    display: 'block',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.25rem',
                  }}>
                    Ruleset
                  </label>
                  <select
                    id="new-save-ruleset"
                    value={rulesetSelection}
                    onChange={(e) => setRulesetSelection(e.target.value)}
                    data-testid="ruleset-select"
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
                    <option value="generic">Generic (Classic Dodger sim)</option>
                    <option value="official_foam">USA Dodgeball 2026.1 — Foam</option>
                    <option value="official_no_sting">USA Dodgeball 2026.1 — No-Sting</option>
                    <option value="official_cloth">USA Dodgeball 2026.1 — Cloth</option>
                  </select>

                  {/* Dynamic Explanation Card */}
                  <div style={{
                    marginTop: '1rem',
                    background: 'rgba(34, 211, 238, 0.04)',
                    borderLeft: '3px solid #22d3ee',
                    padding: '0.75rem 1rem',
                    borderRadius: '0 4px 4px 0',
                  }}>
                    <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc' }}>
                      {rulesetExplanations[rulesetSelection].title}
                    </h4>
                    <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
                      {rulesetExplanations[rulesetSelection].desc}
                    </p>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: '#22d3ee', fontWeight: 600 }}>
                      {rulesetExplanations[rulesetSelection].bullet}
                    </p>
                  </div>

                  <p style={{ fontSize: '0.6875rem', color: '#64748b', margin: '0.375rem 0 0' }}>
                    Set at career creation only. Cannot be changed later.
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
            {view === 'build_coach' && <CoachStep coach={buildCoach} setCoach={setBuildCoach} onBack={() => setView('build_identity')} onNext={() => setView('build_roster')} />}
            {view === 'build_roster' && <StartingRecruitmentStep onCommit={handleBuildFromScratch} onBack={() => setView('build_coach')} creating={creating} />}
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

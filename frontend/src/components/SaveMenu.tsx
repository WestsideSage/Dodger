import { useCallback, useEffect, useState } from 'react';
import type { SaveInfo, SaveListResponse, ClubOption } from '../types';
import { IdentityStep } from './new-game/IdentityStep';
import { CoachStep } from './new-game/CoachStep';
import { StartingRecruitmentStep } from './new-game/StartingRecruitmentStep';

interface SaveMenuProps {
  onSaveLoaded: () => void;
}

type View = 'list' | 'new' | 'takeover' | 'build_identity' | 'build_coach' | 'build_roster';

export function SaveMenu({ onSaveLoaded }: SaveMenuProps) {
  const [view, setView] = useState<View>('list');
  const [saves, setSaves] = useState<SaveInfo[]>([]);
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

  const [deleting, setDeleting] = useState<string | null>(null);

  const loadSaveList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/saves');
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data: SaveListResponse = await res.json();
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
      const res = await fetch('/api/saves/clubs');
      if (res.ok) {
        const data = await res.json();
        setClubs(data.clubs);
        if (data.clubs.length > 0) setNewClubId(data.clubs[0].club_id);
      }
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
      const res = await fetch('/api/saves/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Load failed');
      }
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
      const res = await fetch('/api/saves/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Delete failed');
      }
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
      const res = await fetch('/api/saves/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), club_id: newClubId }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create save');
      }
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
      const res = await fetch('/api/saves/build-from-scratch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          save_name: buildIdentity.save_name,
          club_name: buildIdentity.club_name,
          city: buildIdentity.city,
          colors: buildIdentity.colors,
          coach_name: buildCoach.coach_name,
          coach_backstory: buildCoach.coach_backstory,
          roster_player_ids: rosterIds
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create custom save');
      }
      onSaveLoaded();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create custom save');
      setCreating(false);
    }
  }

  return (
    <div
      data-testid="save-menu"
      style={{
        display: 'flex',
        minHeight: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#020617',
        padding: '2.5rem 1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '32rem' }}>
        {/* Title block */}
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <p style={{
            fontFamily: 'var(--font-mono-data)',
            textTransform: 'uppercase',
            letterSpacing: '0.22em',
            fontSize: '0.75rem',
            color: '#22d3ee',
            margin: '0 0 0.25rem',
          }}>
            Dynasty simulator
          </p>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontSize: '2.25rem',
            color: '#ffffff',
            margin: 0,
          }}>
            Dodgeball Manager
          </h1>
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
                {loading ? (
                  <p style={{ padding: '1.5rem 0', textAlign: 'center', fontSize: '0.875rem', color: '#64748b' }}>
                    Loading saves…
                  </p>
                ) : saves.length === 0 ? (
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
                        color: '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      Start New Game
                    </button>
                  </div>
                ) : (
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {saves.map((save) => (
                      <li
                        key={save.path}
                        data-testid="save-item"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          padding: '0.75rem 0',
                          borderBottom: '1px solid #1e293b',
                          opacity: activePath === save.path ? 1 : 0.9,
                        }}
                      >
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
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.125rem' }}>
                            {save.club_name ?? save.club_id ?? 'Unknown club'}
                            {save.week != null && ` · Week ${save.week}`}
                          </div>
                        </div>
                        <button
                          onClick={() => handleLoad(save.path)}
                          disabled={activePath === save.path}
                          data-testid="load-save-btn"
                          style={{
                            borderRadius: '4px',
                            border: '1px solid #334155',
                            background: '#1e293b',
                            padding: '0.25rem 0.75rem',
                            fontSize: '0.6875rem',
                            fontFamily: 'var(--font-display)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.075em',
                            color: '#cbd5e1',
                            cursor: 'pointer',
                            opacity: activePath === save.path ? 0.4 : 1,
                          }}
                        >
                          {activePath === save.path ? 'Loaded' : 'Load'}
                        </button>
                        {save.path !== 'dodgeball_sim.db' && (
                          <button
                            onClick={() => handleDelete(save.path)}
                            disabled={deleting === save.path}
                            data-testid="delete-save-btn"
                            style={{
                              borderRadius: '4px',
                              border: '1px solid rgba(244,63,94,0.3)',
                              background: 'rgba(244,63,94,0.08)',
                              padding: '0.25rem 0.75rem',
                              fontSize: '0.6875rem',
                              fontFamily: 'var(--font-display)',
                              textTransform: 'uppercase',
                              letterSpacing: '0.075em',
                              color: '#fb7185',
                              cursor: 'pointer',
                              opacity: deleting === save.path ? 0.4 : 1,
                            }}
                          >
                            {deleting === save.path ? '…' : 'Delete'}
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {view === 'new' && (
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  onClick={() => setView('takeover')}
                  style={{
                    flex: 1, padding: '2rem 1rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#e2e8f0', cursor: 'pointer', textAlign: 'center'
                  }}
                >
                  <h3 style={{ margin: '0 0 0.5rem', color: '#22d3ee' }}>Take Over a Program</h3>
                  <p style={{ margin: 0, fontSize: '0.875rem', color: '#94a3b8' }}>Select an existing franchise and lead them to glory.</p>
                </button>
                <button
                  onClick={() => setView('build_identity')}
                  style={{
                    flex: 1, padding: '2rem 1rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#e2e8f0', cursor: 'pointer', textAlign: 'center'
                  }}
                >
                  <h3 style={{ margin: '0 0 0.5rem', color: '#f97316' }}>Build from Scratch</h3>
                  <p style={{ margin: 0, fontSize: '0.875rem', color: '#94a3b8' }}>Define a custom identity, coach, and recruit your starting 10.</p>
                </button>
              </div>
            )}

            {view === 'takeover' && (
              <form
                onSubmit={handleCreate}
                data-testid="new-game-form"
                style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
              >
                <div>
                  <label style={{
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
                  <label style={{
                    display: 'block',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-display)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: '#64748b',
                    marginBottom: '0.25rem',
                  }}>
                    Club
                  </label>
                  {clubs.length > 0 ? (
                    <ul style={{
                      listStyle: 'none',
                      padding: 0,
                      margin: 0,
                      border: '1px solid #1e293b',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}>
                      {clubs.map((club) => (
                        <li
                          key={club.club_id}
                          onClick={() => setNewClubId(club.club_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            padding: '0.75rem',
                            cursor: 'pointer',
                            borderBottom: '1px solid #1e293b',
                            borderLeft: newClubId === club.club_id ? '2px solid #f97316' : '2px solid transparent',
                            background: newClubId === club.club_id ? 'rgba(249,115,22,0.08)' : 'transparent',
                            transition: 'background 0.1s',
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>{club.name}</div>
                            {club.tagline && (
                              <div style={{ fontSize: '0.75rem', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{club.tagline}</div>
                            )}
                          </div>
                          {newClubId === club.club_id && (
                            <span style={{ color: '#f97316', fontSize: '0.75rem' }}>✓</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <select
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

                {createError && (
                  <p style={{ fontSize: '0.875rem', color: '#fb7185', margin: 0 }}>{createError}</p>
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

            {view === 'build_identity' && <IdentityStep identity={buildIdentity} setIdentity={setBuildIdentity} onNext={() => setView('build_coach')} />}
            {view === 'build_coach' && <CoachStep coach={buildCoach} setCoach={setBuildCoach} onBack={() => setView('build_identity')} onNext={() => setView('build_roster')} />}
            {view === 'build_roster' && <StartingRecruitmentStep onCommit={handleBuildFromScratch} onBack={() => setView('build_coach')} creating={creating} />}
            {createError && view.startsWith('build_') && <p style={{ fontSize: '0.875rem', color: '#fb7185', marginTop: '1rem' }}>{createError}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

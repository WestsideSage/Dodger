import { useCallback, useEffect, useState } from 'react';
import type { SaveInfo, SaveListResponse, ClubOption } from '../types';

interface SaveMenuProps {
  onSaveLoaded: () => void;
}

type View = 'list' | 'new';

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

  return (
    <div
      data-testid="save-menu"
      className="flex min-h-screen items-center justify-center bg-[var(--color-canvas)] px-4 py-10"
    >
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <p className="font-display uppercase tracking-[0.22em] text-xs text-[var(--color-brick)] mb-1">
            Dynasty simulator
          </p>
          <h1 className="font-display uppercase tracking-widest text-4xl text-[var(--color-charcoal)]">
            Dodgeball Manager
          </h1>
        </div>

        <div className="bg-[var(--color-paper)] border border-[var(--color-border)] rounded-md shadow-[var(--shadow-panel)]">
          {/* Tab bar */}
          <div className="flex border-b border-[var(--color-border)]">
            <button
              onClick={() => setView('list')}
              className={`flex-1 py-3 text-sm font-display uppercase tracking-wider transition-colors ${
                view === 'list'
                  ? 'text-[var(--color-brick)] border-b-2 border-[var(--color-brick)] -mb-px'
                  : 'text-[var(--color-muted)] hover:text-[var(--color-charcoal)]'
              }`}
            >
              Load Game
            </button>
            <button
              onClick={() => setView('new')}
              data-testid="new-game-tab"
              className={`flex-1 py-3 text-sm font-display uppercase tracking-wider transition-colors ${
                view === 'new'
                  ? 'text-[var(--color-brick)] border-b-2 border-[var(--color-brick)] -mb-px'
                  : 'text-[var(--color-muted)] hover:text-[var(--color-charcoal)]'
              }`}
            >
              New Game
            </button>
          </div>

          <div className="p-5">
            {error && (
              <div className="mb-4 rounded border border-[var(--color-danger)] bg-[var(--color-danger)]/10 p-3 text-sm text-[var(--color-danger)]">
                {error}
              </div>
            )}

            {view === 'list' && (
              <div data-testid="save-list">
                {loading ? (
                  <p className="py-6 text-center text-sm text-[var(--color-muted)]">Loading saves…</p>
                ) : saves.length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-sm text-[var(--color-muted)] mb-4">No saves found.</p>
                    <button
                      onClick={() => setView('new')}
                      className="rounded-md bg-[var(--color-brick)] px-5 py-2 text-sm font-display uppercase tracking-wider text-[var(--color-paper)] hover:opacity-90 transition-opacity"
                    >
                      Start New Game
                    </button>
                  </div>
                ) : (
                  <ul className="divide-y divide-[var(--color-border)]">
                    {saves.map((save) => (
                      <li
                        key={save.path}
                        data-testid="save-item"
                        className={`flex items-center gap-3 py-3 ${
                          activePath === save.path ? 'opacity-100' : 'opacity-90'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-[var(--color-charcoal)] truncate">
                            {save.name}
                            {activePath === save.path && (
                              <span className="ml-2 text-xs text-[var(--color-brick)] font-display uppercase tracking-wider">
                                active
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-[var(--color-muted)] mt-0.5">
                            {save.club_name ?? save.club_id ?? 'Unknown club'}
                            {save.week != null && ` · Week ${save.week}`}
                          </div>
                        </div>
                        <button
                          onClick={() => handleLoad(save.path)}
                          disabled={activePath === save.path}
                          data-testid="load-save-btn"
                          className="rounded border border-[var(--color-border)] px-3 py-1 text-xs font-display uppercase tracking-wider hover:bg-[var(--color-brick)] hover:text-[var(--color-paper)] hover:border-[var(--color-brick)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {activePath === save.path ? 'Loaded' : 'Load'}
                        </button>
                        {save.path !== 'dodgeball_sim.db' && (
                          <button
                            onClick={() => handleDelete(save.path)}
                            disabled={deleting === save.path}
                            data-testid="delete-save-btn"
                            className="rounded border border-[var(--color-border)] px-3 py-1 text-xs font-display uppercase tracking-wider text-[var(--color-muted)] hover:bg-[var(--color-danger)] hover:text-[var(--color-paper)] hover:border-[var(--color-danger)] transition-colors disabled:opacity-40"
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
              <form
                onSubmit={handleCreate}
                data-testid="new-game-form"
                className="flex flex-col gap-4"
              >
                <div>
                  <label className="block text-xs font-display uppercase tracking-wider text-[var(--color-muted)] mb-1">
                    Save Name
                  </label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="My Career"
                    data-testid="save-name-input"
                    className="w-full rounded border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 py-2 text-sm text-[var(--color-charcoal)] focus:outline-none focus:ring-1 focus:ring-[var(--color-brick)]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-display uppercase tracking-wider text-[var(--color-muted)] mb-1">
                    Club
                  </label>
                  {clubs.length > 0 ? (
                    <ul className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded">
                      {clubs.map((club) => (
                        <li
                          key={club.club_id}
                          onClick={() => setNewClubId(club.club_id)}
                          className={`flex items-center gap-3 px-3 py-3 cursor-pointer transition-colors ${
                            newClubId === club.club_id
                              ? 'bg-[var(--color-brick)]/10 border-l-2 border-[var(--color-brick)]'
                              : 'hover:bg-[var(--color-canvas)]'
                          }`}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-[var(--color-charcoal)]">{club.name}</div>
                            {club.tagline && (
                              <div className="text-xs text-[var(--color-muted)] truncate">{club.tagline}</div>
                            )}
                          </div>
                          {newClubId === club.club_id && (
                            <span className="text-[var(--color-brick)] text-xs">✓</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <select
                      value={newClubId}
                      onChange={(e) => setNewClubId(e.target.value)}
                      className="w-full rounded border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 py-2 text-sm"
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
                  <p className="text-sm text-[var(--color-danger)]">{createError}</p>
                )}

                <button
                  type="submit"
                  disabled={creating}
                  data-testid="create-save-btn"
                  className="rounded-md bg-[var(--color-brick)] px-5 py-2.5 text-sm font-display uppercase tracking-wider text-[var(--color-paper)] hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {creating ? 'Creating…' : 'Start Career'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

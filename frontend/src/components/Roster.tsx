import { useMemo, useState } from 'react';
import type { Player, RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { PageHeader, StatChip, StatusMessage, RatingBar } from './ui';
import { PlayerTheaterRow } from './roster/PlayerTheaterRow';
import { PlayerCompactRow } from './roster/PlayerCompactRow';
import { PotentialBadge } from './roster/PotentialBadge';

export function Roster() {
  const { data, loading, error } = useApiResource<RosterResponse>('/api/roster');
  const [isCompact, setIsCompact] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  // A dodgeball lineup fields 6 starters; the rest of the ordered lineup is bench.
  const defaultLineupIds = useMemo(
    () => new Set((data?.default_lineup ?? []).slice(0, 6)),
    [data?.default_lineup]
  );

  const roster = useMemo(
    () => (data?.roster ?? [])
      .map(player => ({ player, starter: defaultLineupIds.has(player.id) }))
      .sort((a, b) => Number(b.starter) - Number(a.starter) || b.player.overall - a.player.overall || a.player.age - b.player.age),
    [data?.roster, defaultLineupIds]
  );

  const starters = useMemo(() => roster.filter(r => r.starter), [roster]);
  const bench = useMemo(() => roster.filter(r => !r.starter), [roster]);

  if (loading) return <StatusMessage title="Loading roster">Building the club sheet.</StatusMessage>;
  if (error) return <StatusMessage title="Roster unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No roster">No roster data returned.</StatusMessage>;

  const averageAge = Math.round(roster.reduce((sum, r) => sum + r.player.age, 0) / roster.length);
  const averageOverall = Math.round(roster.reduce((sum, r) => sum + r.player.overall, 0) / roster.length);

  return (
    <div className="dm-panel">
      <PageHeader
        eyebrow="Roster Lab"
        title="Team Roster"
        description="Player condition, role fit, and match readiness. Click any player row to view their detailed profile."
        stats={
          <>
            <StatChip label="Avg Age" value={averageAge} />
            <StatChip label="Avg OVR" value={averageOverall} tone="info" />
            <StatChip label="Starters" value={starters.length} />
            <button
              onClick={() => setIsCompact(!isCompact)}
              style={{ padding: '0.5rem 0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#cbd5e1', cursor: 'pointer', fontSize: '0.75rem', textTransform: 'uppercase' }}
            >
              {isCompact ? 'Theater View' : 'Compact View'}
            </button>
          </>
        }
      />

      {/* 1. Starting Lineup Table */}
      <div style={{ marginTop: '2rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#22d3ee', margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Starting Lineup <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#94a3b8' }}>({starters.length} Players)</span>
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.825rem', color: '#64748b' }}>These players will start in active matches unless swapped or injured.</p>
        <table className="dm-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          {!isCompact && (
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Player</th>
                <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Ratings</th>
                <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Potential</th>
                <th style={{ padding: '1rem', textAlign: 'right', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>OVR</th>
                <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Role</th>
              </tr>
            </thead>
          )}
          {isCompact && (
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Name</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>ACC</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>POW</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>DOD</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>CAT</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>OVR</th>
                <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Role</th>
              </tr>
            </thead>
          )}
          <tbody>
            {starters.map(({ player, starter }) => (
              isCompact ? (
                <PlayerCompactRow key={player.id} player={player} starter={starter} onClick={() => setSelectedPlayer(player)} />
              ) : (
                <PlayerTheaterRow key={player.id} player={player} starter={starter} onClick={() => setSelectedPlayer(player)} />
              )
            ))}
          </tbody>
        </table>
      </div>

      {/* 2. Bench & Reserves Table */}
      <div style={{ marginTop: '3rem', marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f97316', margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Bench & Reserves <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#94a3b8' }}>({bench.length} Players)</span>
        </h3>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.825rem', color: '#64748b' }}>Backup roster depth. Swapped into starters to manage fatigue or counter specific strategies.</p>
        
        {bench.length === 0 ? (
          <div style={{
            background: '#0b1329',
            border: '1px dashed #1e293b',
            borderRadius: '8px',
            padding: '2rem',
            textAlign: 'center',
            color: '#94a3b8',
          }}>
            <p style={{ margin: '0 0 0.5rem 0', fontWeight: 600, color: '#cbd5e1' }}>No bench players or reserves in the roster.</p>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>You can recruit new prospects and add roster depth during the offseason recruitment phase to bolster your club!</p>
          </div>
        ) : (
          <table className="dm-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            {!isCompact && (
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                  <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Player</th>
                  <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Ratings</th>
                  <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Potential</th>
                  <th style={{ padding: '1rem', textAlign: 'right', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>OVR</th>
                  <th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Role</th>
                </tr>
              </thead>
            )}
            {isCompact && (
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Name</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>ACC</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>POW</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>DOD</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>CAT</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>OVR</th>
                  <th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Role</th>
                </tr>
              </thead>
            )}
            <tbody>
              {bench.map(({ player, starter }) => (
                isCompact ? (
                  <PlayerCompactRow key={player.id} player={player} starter={starter} onClick={() => setSelectedPlayer(player)} />
                ) : (
                  <PlayerTheaterRow key={player.id} player={player} starter={starter} onClick={() => setSelectedPlayer(player)} />
                )
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 3. Premium Player Profile Modal */}
      {selectedPlayer && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(2, 6, 23, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '1.5rem',
        }}>
          <div style={{
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '12px',
            width: '100%',
            maxWidth: '650px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)',
              padding: '1.5rem',
              borderBottom: '1px solid #1e293b',
              position: 'relative',
            }}>
              <button 
                onClick={() => setSelectedPlayer(null)}
                style={{
                  position: 'absolute',
                  top: '1.5rem',
                  right: '1.5rem',
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '1.25rem',
                }}
              >
                ✕
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                  fontSize: '2rem',
                  fontWeight: 900,
                  color: '#38bdf8',
                  background: 'rgba(56, 189, 248, 0.1)',
                  padding: '0.5rem 1rem',
                  borderRadius: '8px',
                }}>
                  #{parseInt(selectedPlayer.id.split('_').at(-1) ?? '0', 10) + 1}
                </div>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {selectedPlayer.name}
                    {selectedPlayer.newcomer && (
                      <span style={{ fontSize: '0.625rem', color: '#a78bfa', border: '1px solid #a78bfa', padding: '0.125rem 0.375rem', borderRadius: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Newcomer
                      </span>
                    )}
                  </h2>
                  <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: '#94a3b8' }}>
                    {selectedPlayer.archetype} · {selectedPlayer.role}
                  </p>
                </div>
              </div>
            </div>

            {/* Body */}
            <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
              {/* Left Column: Bio & Weekly History */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Biographical & Status</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.875rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Age</span>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>{selectedPlayer.age} years old</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Overall Rating</span>
                      <span style={{ color: '#22d3ee', fontWeight: 800 }}>{selectedPlayer.overall} OVR</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#94a3b8' }}>Potential</span>
                      <PotentialBadge tier={selectedPlayer.potential_tier} confidence={selectedPlayer.scouting_confidence} />
                    </div>
                  </div>
                </div>

                <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Progression Sparkline</h4>
                  {selectedPlayer.weekly_ovr_history && selectedPlayer.weekly_ovr_history.length > 0 ? (
                    <>
                      <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '60px', padding: '8px 0' }}>
                        {selectedPlayer.weekly_ovr_history.map((ovr, i) => (
                          <div 
                            key={i} 
                            title={`Week ${i+1}: ${ovr}`}
                            style={{
                              flex: 1,
                              background: '#22d3ee',
                              height: `${((ovr - 30) / 70) * 100}%`,
                              minHeight: '4px',
                              borderRadius: '2px',
                              opacity: i === selectedPlayer.weekly_ovr_history.length - 1 ? 1 : 0.6,
                            }}
                          />
                        ))}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                        <span>Initial: {selectedPlayer.weekly_ovr_history[0] || selectedPlayer.overall}</span>
                        <span>Current: {selectedPlayer.overall}</span>
                      </div>
                    </>
                  ) : (
                    <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>No progression history available yet.</p>
                  )}
                </div>
              </div>

              {/* Right Column: Ratings Bars */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Skill Ratings</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Accuracy</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.accuracy}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.accuracy} compact />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Power</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.power}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.power} compact />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Dodge</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.dodge}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.dodge} compact />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Catch</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.catch}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.catch} compact />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Stamina</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.stamina}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.stamina} compact />
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#cbd5e1' }}>Tactical IQ</span>
                        <span style={{ color: '#22d3ee', fontWeight: 600 }}>{selectedPlayer.ratings.tactical_iq}</span>
                      </div>
                      <RatingBar rating={selectedPlayer.ratings.tactical_iq} compact />
                    </div>

                    {/* V2 Advanced ratings if available */}
                    {selectedPlayer.ratings.catch_courage !== undefined && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                          <span style={{ color: '#cbd5e1' }}>Catch Courage</span>
                          <span style={{ color: '#a78bfa', fontWeight: 600 }}>{selectedPlayer.ratings.catch_courage}</span>
                        </div>
                        <RatingBar rating={selectedPlayer.ratings.catch_courage} compact />
                      </div>
                    )}
                    {selectedPlayer.ratings.throw_selection_iq !== undefined && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                          <span style={{ color: '#cbd5e1' }}>Throw Selection IQ</span>
                          <span style={{ color: '#a78bfa', fontWeight: 600 }}>{selectedPlayer.ratings.throw_selection_iq}</span>
                        </div>
                        <RatingBar rating={selectedPlayer.ratings.throw_selection_iq} compact />
                      </div>
                    )}
                    {selectedPlayer.ratings.conditioning_curve !== undefined && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                          <span style={{ color: '#cbd5e1' }}>Conditioning Curve</span>
                          <span style={{ color: '#a78bfa', fontWeight: 600 }}>{selectedPlayer.ratings.conditioning_curve}</span>
                        </div>
                        <RatingBar rating={selectedPlayer.ratings.conditioning_curve} compact />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid #1e293b',
              background: '#090d16',
              display: 'flex',
              justifyContent: 'flex-end',
            }}>
              <button 
                onClick={() => setSelectedPlayer(null)}
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#cbd5e1', cursor: 'pointer' }}
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

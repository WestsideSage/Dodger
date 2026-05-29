import { useState } from 'react';
import type { Player } from '../types';
import { RatingBar, ActionButton } from './ui';

export function PlayerDetailModal({
  player,
  onClose,
}: {
  player: Player;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<'overview' | 'ratings' | 'more'>('overview');

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
      onClick={onClose}
    >
      <div
        className="dm-panel"
        style={{
          width: '100%',
          maxWidth: '32rem',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderRadius: '8px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: '1.25rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span className="dm-kicker">Player Card</span>
            <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', color: '#fff', fontSize: '1.5rem', textTransform: 'uppercase' }}>
              {player.name}
            </h2>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.25rem', color: '#94a3b8', fontSize: '0.875rem' }}>
              <span>OVR {player.overall}</span>
              <span>·</span>
              <span>Age {player.age}</span>
              <span>·</span>
              <span style={{ color: '#22d3ee' }}>{player.role}</span>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1.25rem' }}>×</button>
        </div>

        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', background: '#0f172a' }}>
          {(['overview', 'ratings', 'more'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
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
                borderBottom: tab === t ? '2px solid #22d3ee' : '2px solid transparent',
                color: tab === t ? '#22d3ee' : '#64748b',
                transition: 'color 0.15s',
              }}
            >
              {t}
            </button>
          ))}
        </div>

        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1 }}>
          {tab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#e2e8f0' }}>Bio</h3>
                <p style={{ margin: 0, fontSize: '0.875rem', color: '#94a3b8' }}>
                  {player.name} is a {player.age}-year-old {player.role.toLowerCase()} with {player.potential_tier.toLowerCase()} potential.
                </p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '4px', border: '1px solid #1e293b' }}>
                  <div className="dm-kicker">Potential</div>
                  <div style={{ fontSize: '1.125rem', color: '#fff', fontWeight: 600 }}>{player.potential_tier}</div>
                  <div style={{ marginTop: '0.35rem', fontSize: '0.8rem', color: '#64748b' }}>
                    Ceiling {player.potential_ceiling}
                    {player.headroom > 0 && (
                      <span style={{ color: '#94a3b8' }}> · +{player.headroom} room</span>
                    )}
                  </div>
                </div>
                <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '4px', border: '1px solid #1e293b' }}>
                  <div className="dm-kicker">Growth</div>
                  <div style={{
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    color: player.projected_growth === 'growing'
                      ? '#10b981'
                      : player.projected_growth === 'declining'
                      ? '#ef4444'
                      : '#94a3b8',
                  }}>
                    {player.projected_growth === 'growing' ? '▲ Growing'
                      : player.projected_growth === 'declining' ? '▼ Declining'
                      : '— Plateauing'}
                  </div>
                  <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#64748b' }}>
                    OVR {player.overall}
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'ratings' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <RatingBar label="Accuracy" rating={player.ratings.accuracy} />
              <RatingBar label="Power" rating={player.ratings.power} />
              <RatingBar label="Dodge" rating={player.ratings.dodge} />
              <RatingBar label="Catch" rating={player.ratings.catch} />
              <RatingBar label="Stamina" rating={player.ratings.stamina} />
              <RatingBar label="Tactical IQ" rating={player.ratings.tactical_iq} />
              {typeof player.ratings.throw_selection_iq === 'number' && (
                <RatingBar
                  label="Throw Selection IQ"
                  rating={player.ratings.throw_selection_iq}
                  explanation="Raises the value threshold a throw must clear before this player commits to it. Higher ratings mean fewer low-percentage and flood throws, and a lower chance of illegal or headshot throws that gift the opponent a catch."
                />
              )}
              {typeof player.ratings.catch_courage === 'number' && (
                <RatingBar
                  label="Catch Courage"
                  rating={player.ratings.catch_courage}
                  explanation="Sets how often this player attempts a catch instead of blocking or dodging an incoming throw. Higher ratings convert more defenses into catch attempts (gaining returns when successful, risking elimination when not), scaled by the team's catch posture."
                />
              )}
            </div>
          )}

          {tab === 'more' && (
            <div style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              <p>Additional stats and historical data will appear here in future updates.</p>
            </div>
          )}
        </div>

        <div style={{ padding: '1rem', borderTop: '1px solid #1e293b', background: '#0f172a', display: 'flex', justifyContent: 'flex-end' }}>
          <ActionButton onClick={onClose}>Close</ActionButton>
        </div>
      </div>
    </div>
  );
}

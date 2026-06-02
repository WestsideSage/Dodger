import { useState } from 'react';
import type { Player } from '../types';
import { RatingBar, ActionButton, Dialog } from './ui';
import { TermTip, ProofChip } from '../legibility';
import type { TermId } from '../legibility';

// Mirrors ROLE_TERM_ID in Roster.tsx — kept in sync with recruitment._RECRUITMENT_DISPLAY_NAMES.
const PLAYER_TERM_ID: Record<string, TermId> = {
  'Sharpshooter':          'archetype.sharpshooter',
  'Net Specialist':        'archetype.net_specialist',
  'Ball Hawk':             'archetype.ball_hawk',
  'Iron Anchor':           'archetype.iron_anchor',
  'Two-Way Threat':        'archetype.two_way_threat',
  'Skirmisher':            'archetype.skirmisher',
  'Possession Specialist': 'archetype.possession_specialist',
  'Hit-and-Run':           'archetype.hit_and_run',
};

export function PlayerDetailModal({
  player,
  onClose,
}: {
  player: Player;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<'overview' | 'ratings' | 'more'>('overview');

  return (
    <Dialog
      label={`${player.name} — player card`}
      labelledBy="player-detail-title"
      onClose={onClose}
      panelClassName="dm-panel"
      panelStyle={{
        width: '100%',
        maxWidth: '32rem',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: '8px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
      }}
    >
        <div style={{ padding: '1.25rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span className="dm-kicker">Player Card</span>
            <h2 id="player-detail-title" style={{ margin: 0, fontFamily: 'var(--font-display)', color: '#fff', fontSize: '1.5rem', textTransform: 'uppercase' }}>
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
                <div style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                }}>
                  <p style={{ margin: 0, fontSize: '0.875rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                    {player.name} is a{' '}
                    <TermTip term={PLAYER_TERM_ID[player.role] ?? 'archetype.sharpshooter'}>
                      <span style={{ color: '#22d3ee', fontWeight: 600 }}>{player.role}</span>
                    </TermTip>
                    {' '}at age {player.age}, with a game built on{' '}
                    <strong style={{ color: '#e2e8f0' }}>{player.bio_strongest_attr?.toLowerCase() || 'accuracy'}</strong>
                    {' '}and{' '}
                    <strong style={{ color: '#e2e8f0' }}>{player.bio_secondary_attr?.toLowerCase() || 'power'}</strong>.
                  </p>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b', lineHeight: 1.4 }}>
                    {player.potential_tier === 'Elite' || player.potential_tier === 'High'
                      ? `${player.headroom > 0 ? `${player.headroom} OVR of headroom ahead — a genuine develop target.` : 'At ceiling. Maximise playing time over long-term growth.'}`
                      : player.projected_growth === 'declining'
                      ? 'Past peak. Deploy as a stabilising veteran while managing workload.'
                      : player.headroom > 0
                      ? 'Solid rotation contributor with room to improve.'
                      : 'Development ceiling reached. Best used as a reliable depth piece.'}
                  </p>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '4px', border: '1px solid #1e293b' }}>
                  <div className="dm-kicker">Potential</div>
                  <div style={{ fontSize: '1.125rem', color: '#fff', fontWeight: 600 }}>{player.potential_tier}</div>
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
                      <TermTip term="growth.ceiling">
                        <span style={{ color: '#94a3b8' }}>Ceiling</span>
                      </TermTip>
                      <span style={{ color: '#e2e8f0', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                        OVR {player.potential_ceiling}
                      </span>
                    </div>
                    {player.headroom > 0 && (
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
                        <TermTip term="growth.headroom">
                          <span style={{ color: '#94a3b8' }}>Headroom</span>
                        </TermTip>
                        <span style={{ color: '#22d3ee', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                          +{player.headroom}
                        </span>
                      </div>
                    )}
                    {player.headroom === 0 && (
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>At ceiling — no headroom remaining.</span>
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
                  {player.projected_growth === 'growing'
                    && player.headroom >= 12
                    && player.age <= 23
                    && (
                    <ProofChip
                      label="High Upside"
                      source={`${player.headroom} OVR of headroom remaining at age ${player.age} — this player has genuine develop-target upside.`}
                    />
                  )}
                  <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#64748b' }}>
                    Current OVR {player.overall}
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
                <TermTip term="attr.throw_selection_iq">
                  <div style={{ textAlign: 'left', width: '100%' }}>
                    <RatingBar label="Throw Selection IQ" rating={player.ratings.throw_selection_iq} />
                  </div>
                </TermTip>
              )}
              {typeof player.ratings.catch_courage === 'number' && (
                <TermTip term="attr.catch_courage">
                  <div style={{ textAlign: 'left', width: '100%' }}>
                    <RatingBar label="Catch Courage" rating={player.ratings.catch_courage} />
                  </div>
                </TermTip>
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
    </Dialog>
  );
}

import { useState } from 'react';
import type { Player } from '../types';
import { RatingBar, ActionButton, Dialog } from './ui';
import { TermTip, ProofChip, getTerm } from '../legibility';
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
  onRelease,
  releaseBlockedReason,
  hasOpenPromise,
}: {
  player: Player;
  onClose: () => void;
  /** Playtest 3 F-8: release this player to free agency. Absent on surfaces
      that only inspect (e.g. read-only contexts). */
  onRelease?: () => Promise<void>;
  /** Why the release is blocked right now (e.g. roster at the 6 floor). */
  releaseBlockedReason?: string | null;
  /** An OPEN promise rides on this player — releasing breaks it. */
  hasOpenPromise?: boolean;
}) {
  const [confirmingRelease, setConfirmingRelease] = useState(false);
  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);
  return (
    <Dialog
      label={`${player.name} — player card`}
      labelledBy="player-detail-title"
      onClose={onClose}
      panelClassName="dm-panel"
      panelStyle={{
        width: '100%',
        maxWidth: '46rem',
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

        {/* Desktop scouting-card layout: overview reads on the left, the full
            rating sheet on the right — no tab-flipping to compare them. */}
        <div
          style={{
            padding: '1.5rem',
            overflowY: 'auto',
            flex: 1,
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 0.95fr)',
            gap: '1.5rem',
            alignItems: 'start',
          }}
        >
          {(
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
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.75rem' }}>
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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <h3 style={{ margin: 0, fontSize: '0.875rem', color: '#e2e8f0' }}>Ratings</h3>
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
                explanation={getTerm('attr.throw_selection_iq').plain}
              />
            )}
            {typeof player.ratings.catch_courage === 'number' && (
              <RatingBar
                label="Catch Courage"
                rating={player.ratings.catch_courage}
                explanation={getTerm('attr.catch_courage').plain}
              />
            )}
          </div>
        </div>

        {/* Playtest 3 F-8: the release confirm strip — the warning carries the
            real consequences (free agency, broken promise) before the click. */}
        {confirmingRelease && onRelease && (
          <div
            data-testid="release-confirm-strip"
            style={{
              padding: '0.8rem 1rem',
              borderTop: '1px solid rgba(244,63,94,0.35)',
              background: 'rgba(244,63,94,0.07)',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#fda4af', fontWeight: 700 }}>
              Release {player.name} to free agency?
            </p>
            <p style={{ margin: '0.2rem 0 0.55rem', fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.45 }}>
              They leave your roster immediately and join the free-agent pool — a rival
              can sign them later.
              {hasOpenPromise && (
                <strong style={{ color: '#fb923c' }}>
                  {' '}You have an OPEN promise to them — releasing breaks it and costs credibility.
                </strong>
              )}
            </p>
            {releaseError && (
              <p style={{ margin: '0 0 0.5rem', fontSize: '0.78rem', color: '#f87171' }}>{releaseError}</p>
            )}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                disabled={releasing}
                onClick={() => {
                  setReleasing(true);
                  setReleaseError(null);
                  onRelease()
                    .catch((err) =>
                      setReleaseError(err instanceof Error ? err.message : 'Release failed'),
                    )
                    .finally(() => setReleasing(false));
                }}
                style={{
                  background: '#be123c', border: 'none', borderRadius: '4px',
                  color: '#fff', fontWeight: 700, padding: '0.4rem 0.9rem',
                  cursor: releasing ? 'not-allowed' : 'pointer', fontSize: '0.8rem',
                }}
              >
                {releasing ? 'Releasing…' : `Yes, release ${player.name}`}
              </button>
              <button
                type="button"
                onClick={() => { setConfirmingRelease(false); setReleaseError(null); }}
                style={{
                  background: 'none', border: '1px solid #334155', borderRadius: '4px',
                  color: '#94a3b8', padding: '0.4rem 0.9rem', cursor: 'pointer', fontSize: '0.8rem',
                }}
              >
                Keep them
              </button>
            </div>
          </div>
        )}

        <div style={{ padding: '1rem', borderTop: '1px solid #1e293b', background: '#0f172a', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
          {onRelease ? (
            <button
              type="button"
              data-testid="release-player-btn"
              disabled={Boolean(releaseBlockedReason) || confirmingRelease}
              title={releaseBlockedReason ?? 'Release this player to free agency'}
              onClick={() => setConfirmingRelease(true)}
              style={{
                background: 'none',
                border: '1px solid rgba(244,63,94,0.45)',
                borderRadius: '4px',
                color: releaseBlockedReason ? '#64748b' : '#fb7185',
                padding: '0.4rem 0.9rem',
                cursor: releaseBlockedReason || confirmingRelease ? 'not-allowed' : 'pointer',
                fontSize: '0.8rem',
                fontWeight: 700,
              }}
            >
              Release to Free Agency
            </button>
          ) : (
            <span />
          )}
          <ActionButton onClick={onClose}>Close</ActionButton>
        </div>
    </Dialog>
  );
}

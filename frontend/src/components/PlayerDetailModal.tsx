import { useState } from 'react';
import type { Player } from '../types';
import { RatingBar, ActionButton, Modal } from '../ui';
import { TermTip, ProofChip, getTerm } from '../legibility';
import type { TermId } from '../legibility';
import styles from './PlayerDetailModal.module.css';

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
    <Modal
      label={`${player.name} — player card`}
      labelledBy="player-detail-title"
      onClose={onClose}
      panelClassName={styles.panel}
    >
        <div className={styles.header}>
          <div>
            <span className={styles.kicker}>Player Card</span>
            <h2 id="player-detail-title" className={styles.playerName}>
              {player.name}
            </h2>
            <div className={styles.headMeta}>
              <span>OVR {player.overall}</span>
              <span>·</span>
              <span>Age {player.age}</span>
              <span>·</span>
              <span className={styles.headRole}>{player.role}</span>
            </div>
          </div>
          <button onClick={onClose} className={styles.closeBtn} aria-label="Close">×</button>
        </div>

        {/* Desktop scouting-card layout: overview reads on the left, the full
            rating sheet on the right — no tab-flipping to compare them. */}
        <div className={styles.body}>
          <div className={styles.overview}>
            <div>
              <h3 className={styles.sectionHead}>Bio</h3>
              <div className={styles.card}>
                <p className={styles.bioText}>
                  {player.name} is a{' '}
                  <TermTip term={PLAYER_TERM_ID[player.role] ?? 'archetype.sharpshooter'}>
                    <span className={styles.bioRole}>{player.role}</span>
                  </TermTip>
                  {' '}at age {player.age}, with a game built on{' '}
                  <strong className={styles.bioStrong}>{player.bio_strongest_attr?.toLowerCase() || 'accuracy'}</strong>
                  {' '}and{' '}
                  <strong className={styles.bioStrong}>{player.bio_secondary_attr?.toLowerCase() || 'power'}</strong>.
                </p>
                <p className={styles.bioNarrative}>
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
            <div className={styles.cards}>
              <div className={styles.statCard}>
                <div className={styles.kicker}>Potential</div>
                <div className={styles.potTier}>{player.potential_tier}</div>
                <div className={styles.potRows}>
                  <div className={styles.potRow}>
                    <TermTip term="growth.ceiling">
                      <span className={styles.potLabel}>Ceiling</span>
                    </TermTip>
                    <span className={styles.potValue}>
                      OVR {player.potential_ceiling}
                    </span>
                  </div>
                  {player.headroom > 0 && (
                    <div className={styles.potRow}>
                      <TermTip term="growth.headroom">
                        <span className={styles.potLabel}>Headroom</span>
                      </TermTip>
                      <span className={styles.potHeadroom}>
                        +{player.headroom}
                      </span>
                    </div>
                  )}
                  {player.headroom === 0 && (
                    <span className={styles.potNote}>At ceiling — no headroom remaining.</span>
                  )}
                </div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.kicker}>Growth</div>
                <div className={`${styles.growthValue} ${
                  player.projected_growth === 'growing'
                    ? styles.growthGrowing
                    : player.projected_growth === 'declining'
                    ? styles.growthDeclining
                    : styles.growthPlateau
                }`}>
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
                <div className={styles.growthCurrent}>
                  Current OVR {player.overall}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.ratingsCol}>
            <h3 className={styles.sectionHead}>Ratings</h3>
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
          <div data-testid="release-confirm-strip" className={styles.releaseStrip}>
            <p className={styles.releaseTitle}>
              Release {player.name} to free agency?
            </p>
            <p className={styles.releaseBody}>
              They leave your roster immediately and join the free-agent pool — a rival
              can sign them later.
              {hasOpenPromise && (
                <strong className={styles.releaseWarn}>
                  {' '}You have an OPEN promise to them — releasing breaks it and costs credibility.
                </strong>
              )}
            </p>
            {releaseError && (
              <p className={styles.releaseError}>{releaseError}</p>
            )}
            <div className={styles.releaseActions}>
              <button
                type="button"
                disabled={releasing}
                className={styles.confirmBtn}
                onClick={() => {
                  setReleasing(true);
                  setReleaseError(null);
                  onRelease()
                    .catch((err) =>
                      setReleaseError(err instanceof Error ? err.message : 'Release failed'),
                    )
                    .finally(() => setReleasing(false));
                }}
              >
                {releasing ? 'Releasing…' : `Yes, release ${player.name}`}
              </button>
              <button
                type="button"
                className={styles.keepBtn}
                onClick={() => { setConfirmingRelease(false); setReleaseError(null); }}
              >
                Keep them
              </button>
            </div>
          </div>
        )}

        <div className={styles.footer}>
          {onRelease ? (
            <button
              type="button"
              data-testid="release-player-btn"
              disabled={Boolean(releaseBlockedReason) || confirmingRelease}
              title={releaseBlockedReason ?? 'Release this player to free agency'}
              onClick={() => setConfirmingRelease(true)}
              className={styles.releaseBtn}
            >
              Release to Free Agency
            </button>
          ) : (
            <span />
          )}
          <ActionButton onClick={onClose}>Close</ActionButton>
        </div>
    </Modal>
  );
}

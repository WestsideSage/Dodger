import { useState, useEffect, useMemo } from 'react';
import { ActionButton } from '../../ui';
import { TermLabel, CeilingGrade } from '../../legibility';
import type { TermId } from '../../legibility';
import { formatOverall, formatPlayerName, formatRole } from '../roster/playerDisplay';
import { saveApi } from '../../api/client';
import type { ProspectOption } from '../../types';
import styles from './StartingRecruitmentStep.module.css';

// Display-string -> archetype term, mirroring Roster.tsx ROLE_TERM_ID (the
// owner's exact complaint: "you can't even see what exactly their archetype
// even does since there is no tooltip").
const ARCHETYPE_TERM_ID: Record<string, TermId> = {
  'Sharpshooter':          'archetype.sharpshooter',
  'Net Specialist':        'archetype.net_specialist',
  'Ball Hawk':             'archetype.ball_hawk',
  'Iron Anchor':           'archetype.iron_anchor',
  'Two-Way Threat':        'archetype.two_way_threat',
  'Skirmisher':            'archetype.skirmisher',
  'Possession Specialist': 'archetype.possession_specialist',
  'Hit-and-Run':           'archetype.hit_and_run',
};

// Soft roster-balance guidance for the build-from-scratch starting draft.
type RoleTrack = 'throwing' | 'catching' | 'survival';

interface RoleInfo {
  label: string;
  roles: RoleTrack[];
}

const ARCHETYPE_ROLES: Record<string, RoleInfo> = {
  'Sharpshooter': { label: 'Thrower', roles: ['throwing'] },
  'Skirmisher': { label: 'Thrower / Survivor', roles: ['throwing', 'survival'] },
  'Net Specialist': { label: 'Catcher', roles: ['catching'] },
  'Iron Anchor': { label: 'Survivor', roles: ['survival'] },
  'Possession Specialist': { label: 'Catcher / Survivor', roles: ['catching', 'survival'] },
  'Ball Hawk': { label: 'Survivor', roles: ['survival'] },
  'Two-Way Threat': { label: 'Thrower / Catcher', roles: ['throwing', 'catching'] },
  'Hit-and-Run': { label: 'Survivor', roles: ['survival'] },
};

const RECOMMENDED: Record<RoleTrack, { min: number; label: string; tip: string }> = {
  throwing: { min: 2, label: 'Throwing', tip: 'Players who can reliably pressure opponents.' },
  catching: { min: 2, label: 'Catching', tip: 'Players who can punish bad throws and protect rallies.' },
  survival: { min: 1, label: 'Survival', tip: 'Players who keep points alive through dodging, stamina, or ball control.' },
};

const ROLE_ORDER: RoleTrack[] = ['throwing', 'catching', 'survival'];

export function StartingRecruitmentStep({
  seed,
  onCommit,
  onBack,
  creating,
}: {
  /** V22 Phase 1: the wizard's creation seed — the list fetched here is
      exactly the pool the build POST (root_seed) drafts from. */
  seed: number;
  onCommit: (ids: string[]) => void;
  onBack: () => void;
  creating: boolean;
}) {
  const [prospects, setProspects] = useState<ProspectOption[]>([]);
  const [rosterIds, setRosterIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    saveApi.startingProspects(seed)
      .then(d => setProspects(d.prospects ?? []))
      .catch(err => setLoadError(err instanceof Error ? err.message : 'Failed to load prospects'));
  }, [seed]);

  const toggleProspect = (id: string) => {
    setRosterIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 10) next.add(id);
      return next;
    });
  };

  // Count role coverage, not unique players: hybrids can help in multiple lanes.
  const compositionTally = useMemo(() => {
    const counts: Record<RoleTrack, number> = { throwing: 0, catching: 0, survival: 0 };
    for (const id of rosterIds) {
      const prospect = prospects.find(p => p.player_id === id);
      const roleInfo = prospect ? ARCHETYPE_ROLES[prospect.public_archetype] : undefined;
      if (roleInfo) {
        for (const role of roleInfo.roles) counts[role] += 1;
      }
    }
    return counts;
  }, [rosterIds, prospects]);

  const hasImbalance = useMemo(() => {
    if (rosterIds.size < 6) return false;
    return ROLE_ORDER.some(role => compositionTally[role] < RECOMMENDED[role].min);
  }, [compositionTally, rosterIds.size]);

  const needed = 6 - rosterIds.size;
  const rosterReady = rosterIds.size >= 6;
  const rosterFull = rosterIds.size >= 10;
  const rosterHelp = rosterReady
    ? rosterFull
      ? 'Roster ready. Remove one player if you want to swap a selection before committing.'
      : 'Roster ready. You can commit now or keep scouting up to 10 players.'
    : rosterIds.size === 0
    ? 'Choose between 6 and 10 players to continue.'
    : `Add ${needed} more player${needed === 1 ? '' : 's'} to continue.`;

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <p className={styles.kicker}>Step 4 of 4</p>
        <h2 className={styles.title}>Recruit Roster</h2>
        <p className={styles.intro}>
          Select at least 6 players (max 10). {rosterIds.size > 0 && `${rosterIds.size} selected.`}
        </p>
        <p className={styles.introFine}>
          This is your own founding class, so nothing is hidden: every card shows the
          full ratings, the <strong>ceiling</strong> they can develop to, and their growth
          arc — the same values their roster row will show after you commit.
        </p>
      </div>

      <div id="composition-guide" className={styles.guide}>
        <div className={styles.guideHead}>
          <span className={styles.guideTitle}>
            Suggested Foundation
          </span>
          {rosterIds.size > 0 && (
            <span className={styles.guideCount}>
              - {rosterIds.size} selected
            </span>
          )}
        </div>
        <div className={styles.chipRow}>
          {ROLE_ORDER.map(role => {
            const rec = RECOMMENDED[role];
            const count = compositionTally[role];
            const met = count >= rec.min;
            const active = rosterIds.size > 0;
            const chipTone = active ? (met ? styles.chipMet : styles.chipUnmet) : '';
            const countTone = active ? (met ? styles.chipCountMet : styles.chipCountUnmet) : '';
            return (
              <div
                key={role}
                title={rec.tip}
                className={`${styles.foundationChip} ${chipTone}`.trim()}
              >
                <div className={styles.chipTop}>
                  <span className={styles.chipLabel}>
                    {rec.label}
                  </span>
                  <span className={`${styles.chipCount} ${countTone}`.trim()}>
                    {count}/{rec.min}+
                  </span>
                </div>
                <div className={styles.chipTip}>
                  {rec.tip}
                </div>
              </div>
            );
          })}
        </div>
        {hasImbalance && (
          <p id="composition-warning" className={styles.imbalanceWarning}>
            Your roster is light in one or more areas. You can still commit, but a balanced first six is easier to manage.
          </p>
        )}
      </div>

      {loadError && (
        <div className={styles.loadError}>
          {loadError}
        </div>
      )}

      {prospects.length === 0 && !loadError && (
        <p className={styles.loadingText}>Loading prospects...</p>
      )}

      <div data-testid="prospect-scroll" className={styles.prospectScroll}>
        {prospects.map(p => {
          const selected = rosterIds.has(p.player_id);
          const canSelect = selected || rosterIds.size < 10;
          const displayName = formatPlayerName(p);
          const displayRole = formatRole(p);
          const displayOverall = formatOverall(p);
          const roleInfo = ARCHETYPE_ROLES[p.public_archetype];
          return (
            <button
              key={p.player_id}
              type="button"
              role="checkbox"
              aria-checked={selected}
              aria-label={`${displayName}, ${p.hometown}, ${displayRole}, overall ${displayOverall}`}
              onClick={() => {
                if (canSelect) toggleProspect(p.player_id);
              }}
              className={`${styles.prospectRow} ${selected ? styles.prospectRowSelected : ''} ${canSelect ? '' : styles.prospectRowDisabled}`.trim()}
            >
              <div className={styles.prospectMain}>
                <div className={styles.prospectNameRow}>
                  <span
                    data-testid={`prospect-name-${p.player_id}`}
                    className={`${styles.prospectName} ${selected ? styles.prospectNameSelected : ''}`.trim()}
                  >
                    {displayName}
                  </span>
                  {typeof p.age === 'number' && (
                    <span className={styles.prospectAge}>Age {p.age}</span>
                  )}
                  {p.ceiling_label && <CeilingGrade grade={p.ceiling_label} />}
                </div>
                <div className={styles.prospectMeta}>
                  {displayRole && (
                    // V22 Phase 5: the archetype finally explains itself —
                    // the journal's "no tooltip" complaint. Rendered as a
                    // non-interactive TermLabel (native `title`), NOT a TermTip:
                    // the whole card is a `<button role="checkbox">`, so a nested
                    // <button> would be an axe nested-interactive violation and a
                    // React validateDOMNesting warning. No stopPropagation wrapper
                    // is needed now that the label is not itself clickable.
                    ARCHETYPE_TERM_ID[p.public_archetype] ? (
                      <TermLabel
                        term={ARCHETYPE_TERM_ID[p.public_archetype]}
                        className={styles.prospectRole}
                      >
                        {displayRole}
                      </TermLabel>
                    ) : (
                      <span className={styles.prospectRole}>{displayRole}</span>
                    )
                  )}
                  {roleInfo && <span className={styles.prospectRoleHint}>({roleInfo.label})</span>}
                </div>
                {p.ratings && (
                  <div className={styles.ratingsStrip}>
                    {([
                      ['ACC', p.ratings.accuracy],
                      ['POW', p.ratings.power],
                      ['DOD', p.ratings.dodge],
                      ['CAT', p.ratings.catch],
                      ['STA', p.ratings.stamina],
                      ['IQ', p.ratings.tactical_iq],
                    ] as Array<[string, number]>).map(([label, value]) => (
                      <span key={label}>
                        {label}{' '}
                        <strong className={value >= 55 ? styles.ratingHigh : styles.ratingLow}>{value}</strong>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className={styles.prospectStats}>
                <div className={styles.statsCol}>
                  <div className={`${styles.ovr} ${selected ? styles.ovrSelected : ''}`.trim()} title="Current overall rating">
                    <strong>{displayOverall}</strong>
                    <span className={styles.ovrUnit}>
                      OVR
                    </span>
                  </div>
                  {typeof p.potential_ceiling === 'number' && (
                    <div
                      className={styles.ceiling}
                      title={`Development ceiling: the highest OVR this player can reach (${p.potential_tier ?? ''} potential).`}
                    >
                      Ceil <strong className={styles.ceilingValue}>{p.potential_ceiling}</strong>
                      {p.potential_tier && (
                        <span className={styles.ceilingTier}>{p.potential_tier}</span>
                      )}
                    </div>
                  )}
                </div>
                <div className={`${styles.checkDot} ${selected ? styles.checkDotSelected : ''}`.trim()}>
                  {selected && <span className={styles.checkMark}>OK</span>}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className={styles.actions}>
        <div className={styles.actionRow}>
          <ActionButton variant="secondary" onClick={onBack} disabled={creating}>Back</ActionButton>
          <ActionButton
            variant="primary"
            onClick={() => onCommit(Array.from(rosterIds))}
            disabled={rosterIds.size < 6 || creating}
            aria-describedby="starting-roster-help"
          >
            {creating ? 'Creating...' : `Next: Commit Roster (${rosterIds.size}/10)`}
          </ActionButton>
        </div>
        <p
          id="starting-roster-help"
          className={`${styles.helper} ${rosterReady ? '' : styles.helperWarning}`.trim()}
        >
          {rosterHelp}
        </p>
      </div>
    </div>
  );
}

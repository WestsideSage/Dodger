import { useState } from 'react';
import type { OffseasonBeat } from '../../types';
import { KnownValue } from '../../legibility/KnownValue';
import { CeilingGrade } from '../../legibility/CeilingGrade';
import { ActionButton, PageHeader, ScrollRegion } from '../../ui';
import styles from './RecruitmentChoice.module.css';
import chrome from '../chrome.module.css';


type RecruitmentBeat = Extract<OffseasonBeat, { key: 'recruitment' }>;

export function RecruitmentChoice({
  beat,
  onSign,
  acting,
}: {
  beat: RecruitmentBeat;
  onSign: (prospectId: string, releasePlayerId?: string) => void;
  acting: boolean;
}) {
  const prospects = beat.payload.available_prospects ?? [];
  const signedCount = beat.payload.signed_count ?? 0;
  const signingLimit = beat.payload.signing_limit ?? 3;
  const remainingSignings = beat.payload.remaining_signings ?? Math.max(0, signingLimit - signedCount);
  const rosterSize = beat.payload.roster_size ?? 0;
  // Fallback mirrors MAX_USER_ROSTER (12) on the backend — a missing field must
  // not render a stale 9-player cap that contradicts the real recruiting gate.
  const rosterLimit = beat.payload.roster_limit ?? 12;
  const [manualSelectedId, setSelectedId] = useState<string | null>(
    prospects[0]?.prospect_id ?? null,
  );
  const [confirmFinish, setConfirmFinish] = useState(false);
  // Playtest 3 F-8 sign-over-cut: at a full roster the Sign action opens the
  // release picker instead of firing immediately.
  const [releasePickerOpen, setReleasePickerOpen] = useState(false);
  const [releaseId, setReleaseId] = useState<string | null>(null);
  const selectedId = prospects.some(prospect => prospect.prospect_id === manualSelectedId)
    ? manualSelectedId
    : (prospects[0]?.prospect_id ?? null);
  const selected = prospects.find(prospect => prospect.prospect_id === selectedId) ?? null;
  const lastSigning = beat.payload.player_signing;
  const signingOutcome = beat.signing_outcome ?? null;
  const releasedPlayer = beat.released_player ?? null;
  const rosterFull = rosterSize >= rosterLimit;
  const userRoster = beat.payload.user_roster ?? [];
  const releaseChoice = userRoster.find(p => p.id === releaseId) ?? null;
  // PT4-06: every prospect that vanishes from the board mid-day must have a
  // named receipt at the desk, not just in the end-of-day class report.
  const rivalSignings = beat.payload.other_signings ?? [];
  // PT4-11: the backend's roster-floor guard, mirrored into the payload so
  // the skip is DISABLED with the reason instead of firing a 409.
  const canSkip = beat.payload.can_skip ?? true;
  const skipBlockedReason = beat.payload.skip_blocked_reason ?? null;

  return (
    <section className={chrome.offseasonShell} data-testid="offseason-recruitment-action">
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title="Signing Day"
        // Codex issue 14: the binding limit is whichever is smaller — class
        // slots or roster space. Say the real capacity up front instead of
        // letting the player plan around three signings with two seats.
        // Playtest 3 F-8: a FULL roster no longer ends recruiting — every
        // pick is a release-to-sign swap, so say that instead of "room for 0".
        // PT5: every club fields six, so a six-player squad is already a COMPLETE
        // lineup — additions are optional bench depth, not a shortfall to fill
        // toward the 12 max. The old "room for N / 6 of 12" copy read as
        // understaffed when the roster was at the league norm.
        description={
          rosterFull
            ? `Roster is full (${rosterSize}/${rosterLimit}) — signing a prospect releases a player you choose. ${remainingSignings} class slot${remainingSignings === 1 ? '' : 's'} remain.`
            : `A six fields a full lineup — your ${rosterSize}-player squad is ready for the season. Signings are optional bench depth: add up to ${Math.min(signingLimit, rosterLimit - rosterSize)} this window (${remainingSignings} class slot${remainingSignings === 1 ? '' : 's'} remain).`
        }
      />

      <article className={`${chrome.dmPanel} ${chrome.offseasonFeature}`}>
        <p className={chrome.dmKicker}>Recruitment Desk</p>
        {/* Fog-of-war truth (V16): prospect ratings are SCOUTED RANGES, never
            the hidden true overall. Free agents are league veterans with
            public records, so their OVR is verified. */}
        {prospects.length > 0 && (
          <p data-testid="signing-day-ovr-disclosure" className={styles.disclosure}>
            Prospect ratings are scouted ranges — the verified OVR is revealed only when they
            sign. Rival clubs bid on prospects too: interest built through scouting, contact
            and visits strengthens your offer. Free agents are league veterans with public
            ratings and sign uncontested. Rivals also sign BETWEEN your picks — a board
            target can be gone by your next slot, so sign your must-haves (especially
            promised players) first.
          </p>
        )}
        {signingOutcome && signingOutcome.kind === 'sniped' && (
          <div data-testid="signing-snipe-banner" className={`${styles.banner} ${styles.bannerSnipe}`}>
            <p className={`${styles.bannerLabel} ${styles.bannerLabelVolt}`}>
              Sniped
            </p>
            <p className={styles.bannerTitle}>
              {signingOutcome.winning_club_name} landed {signingOutcome.prospect_name}
            </p>
            <p className={styles.bannerBody}>
              {signingOutcome.explanation} Your signing slot was not used — pick from the
              remaining class.
            </p>
          </div>
        )}
        {rivalSignings.length > 0 && (
          <div data-testid="signing-rival-board" className={`${styles.banner} ${styles.bannerRival}`}>
            <p className={`${styles.bannerLabel} ${styles.bannerLabelMuted}`}>
              Off the board — rival signings so far
            </p>
            <p className={styles.bannerBody}>
              {rivalSignings.map((s, i) => (
                <span key={`${s.name}-${i}`}>
                  {i > 0 && <span className={styles.rivalSep}> · </span>}
                  <strong className={styles.rivalName}>{s.name}</strong>
                  {s.club_name ? ` → ${s.club_name}` : ''}
                </span>
              ))}
            </p>
          </div>
        )}
        {releasedPlayer && (
          <div data-testid="signing-release-banner" className={`${styles.banner} ${styles.bannerRelease}`}>
            <p className={`${styles.bannerLabel} ${styles.bannerLabelMuted}`}>
              Released
            </p>
            <p className={styles.bannerTitle}>
              {releasedPlayer.name} ({releasedPlayer.overall} OVR, age {releasedPlayer.age}) is now a free agent.
            </p>
            {beat.released_broken_promise && (
              <p className={styles.bannerWarn}>
                Your open promise to them is BROKEN — that costs credibility.
              </p>
            )}
          </div>
        )}
        {signingOutcome && signingOutcome.kind === 'signed' && (
          <div data-testid="signing-win-banner" className={`${styles.banner} ${styles.bannerWin}`}>
            <p className={`${styles.bannerLabel} ${styles.bannerLabelOk}`}>
              Contested Round Won
            </p>
            <p className={styles.bannerBody}>
              {signingOutcome.explanation}
            </p>
            {signingOutcome.reveal && (
              <p data-testid="signing-reveal-line" className={styles.bannerReveal}>
                {signingOutcome.reveal}
              </p>
            )}
          </div>
        )}
        <div className={styles.statGrid}>
          <div className={styles.statTile}>
            <p className={styles.statLabel}>Signing Progress</p>
            <p className={styles.statValue}>{signedCount} / {signingLimit} added</p>
          </div>
          <div className={styles.statTile}>
            <p className={styles.statLabel}>Roster Size</p>
            <p className={styles.statValue}>{rosterSize} / {rosterLimit}</p>
          </div>
        </div>
        {lastSigning && (
          <div className={styles.latest}>
            <p className={styles.latestLabel}>Latest Signing</p>
            <p className={styles.latestName}>{lastSigning.name}</p>
            <p className={styles.latestMeta}>
              OVR {lastSigning.ovr}{lastSigning.age ? ` | Age ${lastSigning.age}` : ''}{lastSigning.role ? ` | ${lastSigning.role}` : ''}
            </p>
          </div>
        )}
        {prospects.length === 0 ? (
          <p className={chrome.offseasonCopy}>
            No prospects remain in the pool. Continue when you are ready to lock the class.
          </p>
        ) : (
          <ScrollRegion maxHeight="26rem" className={styles.prospectList}>
            {prospects.map(prospect => {
              const isSelected = prospect.prospect_id === selectedId;
              return (
                <button
                  key={prospect.prospect_id}
                  type="button"
                  data-testid="recruitment-prospect-row"
                  onClick={() => setSelectedId(prospect.prospect_id)}
                  className={`${styles.prospectRow} ${isSelected ? styles.prospectRowSelected : ''}`}
                >
                  <div className={styles.prospectMain}>
                    <p className={styles.prospectName}>
                      {prospect.name}
                      {/* Codex issue 13: a target carrying an open promise is
                          flagged so the manager signs them before rivals can. */}
                      {prospect.promised && (
                        <span data-testid="signing-promise-badge" className={`${styles.tagBadge} ${styles.tagPromise}`}>
                          Promise at stake
                        </span>
                      )}
                      {prospect.kind === 'free_agent' && ' '}
                      {prospect.kind === 'free_agent' && (
                        <span className={`${styles.tagBadge} ${styles.tagFreeAgent}`}>
                          Free Agent
                        </span>
                      )}
                    </p>
                    <p className={styles.prospectMeta}>
                      {prospect.archetype} · {prospect.hometown} · Age {prospect.age}
                    </p>
                    {/* V24 Phase 7: the same motivation grades + dealbreaker the
                        in-season board showed — the picker never knows less. */}
                    {prospect.motivations && prospect.motivations.length > 0 && (
                      <div className={styles.badgeRow}>
                        {prospect.motivations.map(m => (
                          <span key={m.motivation} className={styles.motivBadge} title={m.receipt}>
                            {m.label} <strong>{m.letter}</strong>
                          </span>
                        ))}
                        {prospect.dealbreaker && (
                          <span
                            className={`${styles.motivBadge} ${prospect.dealbreaker.veto ? styles.motivBadgeVeto : styles.motivBadgeDealbreaker}`}
                            title={prospect.dealbreaker.receipt}
                          >
                            ★ {prospect.dealbreaker.label} {prospect.dealbreaker.letter}
                            {prospect.dealbreaker.veto ? " — WON'T VERBAL" : ''}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className={styles.prospectRight}>
                    {prospect.kind === 'prospect' && prospect.public_ovr_band ? (
                      <>
                        <KnownValue
                          state={prospect.scouted ? 'known' : 'estimated'}
                          label="ovr"
                          value={`${prospect.public_ovr_band[0]}–${prospect.public_ovr_band[1]}`}
                          hint="Scout to narrow"
                        />
                        {typeof prospect.interest === 'number' && (
                          <div className={styles.interest}>
                            Interest {prospect.interest}%
                          </div>
                        )}
                        {/* Playtest 3 elite reveal: the same scout-gated
                            growth-arc grade the in-season board shows. */}
                        {prospect.ceiling_label && (
                          <div className={styles.ceilingWrap}>
                            <CeilingGrade grade={prospect.ceiling_label} />
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className={`${chrome.dmData} ${styles.verifiedOvr}`}>
                          {prospect.overall}
                        </div>
                        <div className={styles.verifiedLabel}>
                          verified ovr
                        </div>
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </ScrollRegion>
        )}
      </article>

      {/* Playtest 3 F-8: the sign-over-cut release picker. Shown when the
          roster is full and the player pressed Sign — the pick goes through
          only with a named release, and the release only commits if the
          contested pick lands (a snipe costs nobody). */}
      {releasePickerOpen && selected && rosterFull && (
        <div data-testid="signing-release-picker" className={styles.releasePicker}>
          <p className={styles.releaseTitle}>
            Roster is full — release someone to sign {selected.name}.
          </p>
          <p className={styles.releaseSub}>
            The release happens only if you win the signing; a snipe costs you nobody.
            The released player joins the free-agent pool.
          </p>
          <ScrollRegion maxHeight="14rem" className={styles.releaseRows}>
            {userRoster.map(p => (
              <label
                key={p.id}
                className={`${styles.releaseRow} ${releaseId === p.id ? styles.releaseRowSelected : ''}`}
              >
                <input
                  type="radio"
                  name="release-choice"
                  checked={releaseId === p.id}
                  onChange={() => setReleaseId(p.id)}
                />
                <span className={styles.releaseName}>{p.name}</span>
                <span className={styles.releaseMeta}>{p.overall} OVR · age {p.age}</span>
                {p.promised && (
                  <span className={styles.releasePromise}>
                    Open promise — releasing breaks it
                  </span>
                )}
              </label>
            ))}
          </ScrollRegion>
          <div className={styles.pickerActions}>
            <button
              type="button"
              disabled={acting || !releaseId}
              onClick={() => {
                if (selectedId && releaseId) {
                  setReleasePickerOpen(false);
                  onSign(selectedId, releaseId);
                }
              }}
              className={`${styles.confirmBtn} ${!releaseId ? styles.confirmBtnDisabled : ''}`}
            >
              {releaseChoice
                ? `Release ${releaseChoice.name} & sign ${selected.name}`
                : 'Pick a player to release'}
            </button>
            <button
              type="button"
              onClick={() => { setReleasePickerOpen(false); setReleaseId(null); }}
              className={styles.cancelBtn}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {confirmFinish && remainingSignings > 0 && (
        <div className={styles.confirmFinish}>
          <p className={styles.confirmFinishTitle}>
            Lock the class with {remainingSignings} slot{remainingSignings === 1 ? '' : 's'} unused?
          </p>
          <p className={styles.confirmFinishBody}>
            Unused signing slots are lost. This cannot be undone.
          </p>
          <div className={styles.confirmFinishActions}>
            <button
              type="button"
              onClick={() => onSign('skip')}
              disabled={acting}
              className={`${styles.lockBtn} ${acting ? styles.lockBtnDisabled : ''}`}
            >
              Yes, lock the class
            </button>
            <button
              type="button"
              onClick={() => setConfirmFinish(false)}
              className={styles.cancelBtn}
            >
              Keep signing
            </button>
          </div>
        </div>
      )}

      <div className={`${chrome.dmPanel} ${chrome.actionBar}`}>
        <div>
          <p className={chrome.dmKicker}>Next action</p>
          <p>
            {remainingSignings > 0
              ? `${remainingSignings} signing slot${remainingSignings === 1 ? '' : 's'} remaining — select a prospect and sign them.`
              : 'All signing slots used. Continue when ready.'}
          </p>
          {!canSkip && skipBlockedReason && (
            <p className={styles.skipReason}>
              {skipBlockedReason}
            </p>
          )}
        </div>
        <div className={chrome.actionButtons}>
          <ActionButton
            variant="primary"
            onClick={() => {
              setConfirmFinish(false);
              // Playtest 3 F-8: a full roster routes through the release
              // picker — the pick needs a named release to go through.
              if (rosterFull) {
                setReleasePickerOpen(true);
                return;
              }
              onSign(selected?.prospect_id ?? '');
            }}
            disabled={acting || prospects.length === 0 || !selected}
          >
            {acting
              ? 'Signing...'
              : selected
              ? rosterFull
                ? `Sign ${selected.name} (release someone)`
                : `Sign ${selected.name}`
              : 'Sign Best Available'}
          </ActionButton>
          {remainingSignings > 0 ? (
            <button
              type="button"
              onClick={() => setConfirmFinish(true)}
              disabled={acting || !canSkip}
              title={!canSkip && skipBlockedReason ? skipBlockedReason : undefined}
              className={`${styles.skipBtn} ${(acting || !canSkip) ? styles.skipBtnDisabled : ''}`}
            >
              {signedCount > 0 ? 'Lock class early' : 'Skip recruiting'}
            </button>
          ) : (
            <ActionButton
              variant="secondary"
              onClick={() => onSign('skip')}
              disabled={acting}
            >
              Continue
            </ActionButton>
          )}
        </div>
      </div>
    </section>
  );
}

import { useEffect, useRef, useState } from 'react';
import { dynastyApi } from '../../api/client';
import type { DynastyOfficeResponse, RecruitingStatus } from '../../types';
import { RecruitingBadge } from './RecruitingBadge';
import { TermTip, PipelineEmblem, KnownValue, CeilingGrade } from '../../legibility';
import type { PipelineTier, TermId } from '../../legibility';
import styles from './ProspectCard.module.css';

type RecruitingProspect = DynastyOfficeResponse['recruiting']['prospects'][number];
type RecruitingBudget = DynastyOfficeResponse['recruiting']['budget'];

// Same precedence as backend compute_recruiting_status. Mirrored here for
// optimistic UI updates -- the server is authoritative on refetch.
const STATUS_PRECEDENCE: RecruitingStatus[] = [
  'UNSCOUTED',
  'SCOUTED',
  'CONTACTED',
  'VISITED',
  'INTERESTED',
  'LOCKED_OUT',
];

function promoteStatus(current: RecruitingStatus, next: RecruitingStatus): RecruitingStatus {
  const ci = STATUS_PRECEDENCE.indexOf(current);
  const ni = STATUS_PRECEDENCE.indexOf(next);
  return ni > ci ? next : current;
}

// Maps the eight recruitment display names (recruitment.py _RECRUITMENT_DISPLAY_NAMES)
// to their TermId for the hover glossary. The Floodlight card renders every
// archetype with one neutral chip tone (the 5-color contract reserves color for
// fit/talent/status), so only the TermId survives the old per-archetype palette.
const ARCHETYPE_MAP: Array<{
  match: string[];
  termId: TermId;
}> = [
  { match: ['sharpshooter'],         termId: 'archetype.sharpshooter' },
  { match: ['skirmisher'],           termId: 'archetype.skirmisher' },
  { match: ['two-way threat'],       termId: 'archetype.two_way_threat' },
  { match: ['net specialist'],       termId: 'archetype.net_specialist' },
  { match: ['possession specialist'],termId: 'archetype.possession_specialist' },
  { match: ['ball hawk'],            termId: 'archetype.ball_hawk' },
  { match: ['hit-and-run'],          termId: 'archetype.hit_and_run' },
  { match: ['iron anchor'],          termId: 'archetype.iron_anchor' },
];

const archetypeBadge = (label: string) => {
  const n = label.toLowerCase();
  const entry = ARCHETYPE_MAP.find((m) => m.match.some((s) => n.includes(s)));
  const termId: TermId = entry?.termId ?? 'archetype.sharpshooter';
  return (
    <TermTip term={termId}>
      <span className={styles.chip}>{label.toUpperCase()}</span>
    </TermTip>
  );
};

export function ProspectCard({
  prospect,
  budget,
  onAction,
  priority,
}: {
  prospect: RecruitingProspect;
  budget: RecruitingBudget;
  onAction: () => void;
  priority: number;
}) {
  const [loading, setLoading] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<'success' | 'error'>('success');
  // WT-28 timer-cleanup: the feedback flash auto-dismisses via setTimeout. Hold
  // the latest timer id so a card unmounting mid-flash (e.g. the board refetches
  // and re-renders) clears it instead of firing setState on an unmounted node.
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    return () => {
      if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
    };
  }, []);
  const serverStatus: RecruitingStatus = prospect.recruiting_status ?? 'UNSCOUTED';
  const [optimisticStatus, setOptimisticStatus] = useState<RecruitingStatus | null>(null);
  const [pending, setPending] = useState(false);
  // If the server-provided status caught up or surpassed our optimistic guess,
  // drop the optimistic override so we always reflect canonical state.
  const displayStatus: RecruitingStatus =
    optimisticStatus && STATUS_PRECEDENCE.indexOf(optimisticStatus) > STATUS_PRECEDENCE.indexOf(serverStatus)
      ? optimisticStatus
      : serverStatus;

  const runAction = (
    verb: 'scoutProspect' | 'contactProspect' | 'visitProspect',
    label: string,
    nextStatus: RecruitingStatus,
  ) => {
    setLoading(true);
    setPending(true);
    const previousOptimistic = optimisticStatus;
    setOptimisticStatus((current) =>
      promoteStatus(current ?? serverStatus, nextStatus),
    );
    dynastyApi[verb](prospect.player_id)
      .then((response) => {
        setFeedbackTone('success');
        // Show the concrete before/after delta, not just "Scouted."
        setFeedbackMessage(response?.result?.headline ?? label);
        if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
        feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 3200);
        onAction();
      })
      .catch((error) => {
        // Revert optimistic update on failure.
        setOptimisticStatus(previousOptimistic);
        setFeedbackTone('error');
        // Codex issue 10: a refused action must be unmistakable — say the
        // action was NOT spent, hold the message longer, and refetch the
        // board so the counters/buttons reflect the true remaining budget
        // (a click against a stale budget is the usual cause).
        const reason = error instanceof Error ? error.message : 'Action failed.';
        setFeedbackMessage(`${reason} — action not spent.`);
        if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
        feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 5200);
        onAction();
      })
      .finally(() => {
        setLoading(false);
        setPending(false);
      });
  };

  const canScout = budget.scout[0] < budget.scout[1];
  const canContact = budget.contact[0] < budget.contact[1];
  const canVisit = budget.visit[0] < budget.visit[1];
  const low = prospect.public_ovr_band?.[0] ?? '?';
  const high = prospect.public_ovr_band?.[1] ?? '?';
  const fitTier = prospect.fit_score >= 80 ? 'strong' : prospect.fit_score >= 65 ? 'neutral' : 'risk';
  const fitLabel = prospect.fit_score >= 80 ? 'Strong Fit' : prospect.fit_score >= 65 ? 'Fair Fit' : 'At Risk';
  const fitAccentClass =
    fitTier === 'strong' ? styles.fitStrong : fitTier === 'neutral' ? styles.fitNeutral : styles.fitRisk;
  // Filter the "Public range …" line — it repeats the OVR band already shown
  // in the meter. Display at most 2 of the remaining evidence strings.
  const evidence = prospect.interest_evidence
    .filter(Boolean)
    .filter((s) => !s.toLowerCase().startsWith('public range'))
    .slice(0, 2);
  const safePipelineTier = (
    Math.min(5, Math.max(1, Math.round(prospect.pipeline_tier ?? 1)))
  ) as PipelineTier;

  // V24 Phase 6: a prospect beyond your Scouting Network is a NAME WITHOUT A
  // SHEET — show who he is and where he's from, but nothing scoutable. The hint
  // says exactly which level opens him; the Scouting Network panel above is how.
  if (prospect.fully_visible === false) {
    return (
      <div className={`${styles.card} ${styles.locked}`} data-testid="prospect-card-locked">
        <div className={styles.head}>
          <div className={styles.id}>
            <span className={styles.name} title={prospect.name}>
              🔒 {prospect.name}
            </span>
            <div className={styles.sub}>
              <span aria-label={`Hometown: ${prospect.hometown}`}>
                <span className={styles.fromLabel}>From</span>
                <span className={styles.fromValue}>{prospect.hometown}</span>
              </span>
              {prospect.reach_band && (
                <>
                  <span className={styles.dot}>·</span>
                  <span className={styles.chip}>{prospect.reach_band} REACH</span>
                </>
              )}
            </div>
          </div>
        </div>
        <p className={styles.hint}>
          {prospect.visibility_hint ?? 'Beyond your Scouting Network — raise your reach to open his sheet.'}
        </p>
      </div>
    );
  }

  return (
    <div className={`${styles.card} ${fitAccentClass}`} data-testid="prospect-card">
      {feedbackMessage && (
        <div
          className={`${styles.feedback} ${feedbackTone === 'success' ? styles.feedbackSuccess : styles.feedbackError}`}
        >
          {feedbackTone === 'success' ? '✓ ' : ''}{feedbackMessage}
        </div>
      )}
      <div className={styles.head}>
        <div className={styles.id}>
          <span className={styles.name} title={prospect.name}>
            {prospect.name}
          </span>
          <div className={styles.sub}>
            <span
              className={styles.rank}
              aria-label={`Board rank ${priority}`}
              title="Your board rank for this prospect — sorted by fit by default"
            >
              #{String(priority).padStart(2, '0')}
            </span>
            <span className={styles.dot}>·</span>
            <span aria-label={`Hometown: ${prospect.hometown}`}>
              <span className={styles.fromLabel}>From</span>
              <span className={styles.fromValue}>{prospect.hometown}</span>
            </span>
            <span className={styles.dot}>·</span>
            {archetypeBadge(prospect.public_archetype || 'Balanced')}
            <span className={styles.dot}>·</span>
            <RecruitingBadge status={displayStatus} pending={pending} />
            {prospect.funnel_stage != null && (
              <>
                <span className={styles.dot}>·</span>
                <span
                  className={styles.chip}
                  title="Your recruiting funnel stage — Open → Shortlist → Top 3 → Verbal"
                >
                  {prospect.funnel_stage}
                </span>
              </>
            )}
            <span className={styles.dot}>·</span>
            <span className={styles.pipeline}>
              <TermTip term="recruit.pipeline">
                <span className={styles.miniLabel}>Pipeline</span>
              </TermTip>
              <PipelineEmblem tier={safePipelineTier} size="sm" />
            </span>
          </div>
        </div>
        <div className={styles.fit} aria-label={`Fit score: ${prospect.fit_score} out of 100`}>
          <TermTip term="recruit.fit">
            <span className="lbl">FIT</span>
          </TermTip>
          <span className={`${styles.fitValue} ${styles[fitTier]}`}>
            {prospect.fit_score}
            <span className={styles.fitUnit}>/100</span>
          </span>
        </div>
      </div>

      <div className={styles.meter}>
        <div className={styles.meterBg}>
          <div className={styles.meterFill} style={{ width: `${prospect.fit_score}%` }} />
        </div>
        <div className={styles.meterLabels}>
          <span>
            <TermTip term="recruit.fit">
              <span>{fitLabel.toUpperCase()}</span>
            </TermTip>
          </span>
          {typeof prospect.interest === 'number' && (
            <span className={styles.mono}>
              <TermTip term="recruit.interest">
                <span>Interest</span>
              </TermTip>
              {' '}{prospect.interest}%
            </span>
          )}
          <KnownValue
            state={prospect.scouted ? 'known' : 'estimated'}
            label="OVR"
            value={`${low}–${high}`}
            hint={prospect.scouted ? undefined : 'Scout to narrow'}
          />
          {/* Playtest 3 elite reveal: scouting also grades the growth arc.
              Rendered only once revealed — the fog stays honest. */}
          {prospect.ceiling_label && <CeilingGrade grade={prospect.ceiling_label} />}
        </div>
      </div>

      {evidence.length > 0 && (
        <div className={styles.evidence}>
          <span className={styles.evidenceBar} />
          <span className="copy">{evidence.join(' · ')}</span>
        </div>
      )}
      {/* V24: what this prospect wants, graded from your real program with a
          receipt on hover. The dealbreaker (★) is hidden until you scout him —
          fail it and he never verbals. */}
      {prospect.motivations && prospect.motivations.length > 0 && (
        <div data-testid="prospect-motivations" className={styles.motivations}>
          {prospect.motivations.map((m) => (
            <span key={m.motivation} className={styles.chip} title={m.receipt}>
              {m.label} <strong>{m.letter}</strong>
            </span>
          ))}
          {prospect.dealbreaker ? (
            <span
              className={`${styles.chip} ${prospect.dealbreaker.veto ? styles.chipBroken : styles.chipTalent}`}
              title={prospect.dealbreaker.receipt}
            >
              ★ {prospect.dealbreaker.label} {prospect.dealbreaker.letter}
              {prospect.dealbreaker.veto ? " — WON'T VERBAL" : ''}
            </span>
          ) : (
            <span
              className={`${styles.chip} ${styles.chipMuted}`}
              title="Scout this prospect to reveal what he cares about most"
            >
              ★ Dealbreaker hidden — scout to reveal
            </span>
          )}
        </div>
      )}
      {/* V24 Phase 5: the in-season interest race — named rival suitors and
          whether you lead. Leading the race compounds your courtship. */}
      {prospect.market_signal && prospect.market_signal.rivals.length > 0 && (
        <div data-testid="prospect-rivals" className={styles.rivals}>
          <span
            className={`${styles.chip} ${prospect.market_signal.leader === 'user' ? styles.chipLead : styles.chipTrail}`}
            title="Your tracked interest vs the strongest rival's pursuit. Leading the race compounds your courtship."
          >
            {prospect.market_signal.leader === 'user'
              ? `YOU LEAD +${prospect.market_signal.user_lead}`
              : `TRAILING ${prospect.market_signal.user_lead}`}
          </span>
          {' '}
          <span>
            Rivals:{' '}
            {prospect.market_signal.rivals.map((r, i) => (
              <span key={r.club_id} title={r.receipt}>
                {i > 0 ? ', ' : ''}
                {r.club_name} ({r.interest})
              </span>
            ))}
          </span>
        </div>
      )}
      {/* V24 Phase 4: the home fixture hosting his campus visit, once scheduled. */}
      {prospect.visit_fixture && (
        <div className={styles.visit}>
          <span className={`${styles.chip} ${styles.chipMuted}`}>VISIT SET</span>
          {' '}Hosting him at your Week {prospect.visit_fixture.week} home game.
        </div>
      )}
      {prospect.active_promise && (
        <div data-testid="prospect-promise-chip" className={styles.promise}>
          <span className={`${styles.chip} ${prospect.active_promise.status === 'broken' ? styles.chipBroken : styles.chipLead}`}>
            {prospect.active_promise.status === 'open'
              ? 'PROMISED'
              : prospect.active_promise.status === 'fulfilled'
                ? 'PROMISE KEPT'
                : 'PROMISE BROKEN'}
          </span>
          <span>
            {PROMISE_TYPE_LABELS[prospect.active_promise.promise_type] ?? prospect.active_promise.promise_type}
          </span>
        </div>
      )}
      <div className={styles.actions}>
        {prospect.funnel_stage != null && (
          <button
            className={`${styles.btn}${prospect.on_focus_list ? ` ${styles.btnPrimary}` : ''}`}
            disabled={loading}
            onClick={() => {
              setLoading(true);
              const wasFocused = prospect.on_focus_list;
              dynastyApi
                .focusProspect(prospect.player_id)
                .then(() => {
                  setFeedbackTone('success');
                  setFeedbackMessage(wasFocused ? 'Removed from focus list.' : 'Added to focus list.');
                  if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
                  feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 2600);
                  onAction();
                })
                .catch((error) => {
                  setFeedbackTone('error');
                  setFeedbackMessage(error instanceof Error ? error.message : 'Focus failed.');
                  if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
                  feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 3200);
                })
                .finally(() => setLoading(false));
            }}
            title="Add to / remove from your focus list. Focusing unlocks Contact; your top targets unlock Visit."
            type="button"
          >
            {prospect.on_focus_list ? '★ Focused' : '☆ Focus'}
          </button>
        )}
        <button
          className={styles.btn}
          disabled={loading || !canScout}
          onClick={() => runAction('scoutProspect', 'Scouted.', 'SCOUTED')}
          title={canScout ? 'Reveal more prospect detail' : 'No Scout slots remain this week'}
          type="button"
        >
          Scout
        </button>
        <button
          className={styles.btn}
          disabled={loading || !canContact || prospect.can_contact === false}
          onClick={() => runAction('contactProspect', 'Contact logged.', 'CONTACTED')}
          title={
            prospect.can_contact === false
              ? 'Add him to your focus list first'
              : canContact
                ? 'Build recruit interest'
                : 'No Contact slots remain this week'
          }
          type="button"
        >
          Contact
        </button>
        <button
          className={`${styles.btn} ${styles.btnPrimary}`}
          disabled={loading || !canVisit || prospect.can_visit === false}
          onClick={() => runAction('visitProspect', 'Visit booked.', 'VISITED')}
          title={
            prospect.can_visit === false
              ? 'Visits are reserved for your top focus targets (Top 3)'
              : canVisit
                ? 'Spend a visit slot — your highest-commitment weekly signal to this prospect'
                : 'No Visit slots remain this week'
          }
          type="button"
        >
          Visit
        </button>
        {/* V19b: promises are mechanical — results feed credibility, which
            feeds interest and your contested Signing Day offer. */}
        <select
          className={styles.btn}
          aria-label={`Make a promise to ${prospect.name}`}
          disabled={loading || Boolean(prospect.active_promise && prospect.active_promise.status === 'open')}
          value=""
          onChange={(event) => {
            const promiseType = event.target.value;
            if (!promiseType) return;
            setLoading(true);
            dynastyApi
              .makePromise(prospect.player_id, promiseType)
              .then(() => {
                setFeedbackTone('success');
                setFeedbackMessage(
                  `Promise made: ${PROMISE_TYPE_LABELS[promiseType] ?? promiseType}. Checked at season's end.`,
                );
                if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
                feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 3200);
                onAction();
              })
              .catch((error) => {
                setFeedbackTone('error');
                setFeedbackMessage(error instanceof Error ? error.message : 'Promise failed.');
                if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
                feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 3200);
              })
              .finally(() => setLoading(false));
          }}
          title={
            prospect.active_promise && prospect.active_promise.status === 'open'
              ? 'A promise to this prospect is already open'
              : 'Commit to something real — checked at season\'s end; kept promises build credibility, broken ones cost more'
          }
        >
          <option value="" disabled>
            Promise…
          </option>
          {(prospect.promise_options ?? []).map((option) => (
            <option key={option} value={option}>
              {PROMISE_TYPE_LABELS[option] ?? option}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// Plain-language promise vocabulary (mirrors DynastyOffice.PROMISE_LABELS).
const PROMISE_TYPE_LABELS: Record<string, string> = {
  early_playing_time: 'Early playing time',
  development_priority: 'Development priority',
  contender_path: "We'll contend",
};

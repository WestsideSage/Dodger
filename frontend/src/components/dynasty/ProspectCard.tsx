import { useEffect, useRef, useState } from 'react';
import { dynastyApi } from '../../api/client';
import type { DynastyOfficeResponse, RecruitingStatus } from '../../types';
import { RecruitingBadge } from './RecruitingBadge';
import { TermTip, PipelineEmblem, KnownValue, CeilingGrade } from '../../legibility';
import type { PipelineTier, TermId } from '../../legibility';

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
// to their badge tone and TermId. Tone groups: orange = aggressive throwers / hybrids;
// violet = catch/possession specialists; cyan = evasion/hawk; slate = anchor.
const ARCHETYPE_MAP: Array<{
  match: string[];
  tone: string;
  termId: TermId;
}> = [
  { match: ['sharpshooter'],         tone: 'dm-badge-orange',  termId: 'archetype.sharpshooter' },
  { match: ['skirmisher'],           tone: 'dm-badge-orange',  termId: 'archetype.skirmisher' },
  { match: ['two-way threat'],       tone: 'dm-badge-orange',  termId: 'archetype.two_way_threat' },
  { match: ['net specialist'],       tone: 'dm-badge-violet',  termId: 'archetype.net_specialist' },
  { match: ['possession specialist'],tone: 'dm-badge-violet',  termId: 'archetype.possession_specialist' },
  { match: ['ball hawk'],            tone: 'dm-badge-cyan',    termId: 'archetype.ball_hawk' },
  { match: ['hit-and-run'],          tone: 'dm-badge-cyan',    termId: 'archetype.hit_and_run' },
  { match: ['iron anchor'],          tone: 'dm-badge-slate',   termId: 'archetype.iron_anchor' },
];

const archetypeBadge = (label: string) => {
  const n = label.toLowerCase();
  const entry = ARCHETYPE_MAP.find((m) => m.match.some((s) => n.includes(s)));
  const tone = entry?.tone ?? 'dm-badge-cyan';
  const termId: TermId = entry?.termId ?? 'archetype.sharpshooter';
  return (
    <TermTip term={termId}>
      <span className={`dm-badge ${tone}`}>{label.toUpperCase()}</span>
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
  // Filter the "Public range …" line — it repeats the OVR band already shown
  // in the meter. Display at most 2 of the remaining evidence strings.
  const evidence = prospect.interest_evidence
    .filter(Boolean)
    .filter((s) => !s.toLowerCase().startsWith('public range'))
    .slice(0, 2);
  const safePipelineTier = (
    Math.min(5, Math.max(1, Math.round(prospect.pipeline_tier ?? 1)))
  ) as PipelineTier;

  return (
    <div className={`do-recruit fit-${fitTier}`} style={{ position: 'relative' }} data-testid="prospect-card">
      {feedbackMessage && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: feedbackTone === 'success' ? 'rgba(16, 185, 129, 0.92)' : 'rgba(244, 63, 94, 0.92)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 800,
            fontSize: '1rem',
            zIndex: 10,
            borderRadius: '6px',
            textAlign: 'center',
            padding: '1rem',
          }}
        >
          {feedbackTone === 'success' ? '✓ ' : ''}{feedbackMessage}
        </div>
      )}
      <div className="do-recruit-head">
        <div className="do-recruit-id">
          <span className="do-recruit-name" title={prospect.name}>
            {prospect.name}
          </span>
          <div className="do-recruit-sub" style={{ flexWrap: 'wrap' }}>
            <span
              aria-label={`Board rank ${priority}`}
              title="Your board rank for this prospect — sorted by fit by default"
              style={{ fontSize: '0.6rem', color: '#64748b', letterSpacing: '0.04em' }}
            >
              #{String(priority).padStart(2, '0')}
            </span>
            <span className="dot">·</span>
            <span aria-label={`Hometown: ${prospect.hometown}`}>
              <span
                style={{
                  fontSize: '0.55rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: '#64748b',
                  marginRight: '0.2rem',
                }}
              >
                From
              </span>
              <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{prospect.hometown}</span>
            </span>
            <span className="dot">·</span>
            {archetypeBadge(prospect.public_archetype || 'Balanced')}
            <span className="dot">·</span>
            <RecruitingBadge status={displayStatus} pending={pending} />
            <span className="dot">·</span>
            <span
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <TermTip term="recruit.pipeline">
                <span
                  style={{
                    fontSize: '0.55rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: '#64748b',
                  }}
                >
                  Pipeline
                </span>
              </TermTip>
              <PipelineEmblem tier={safePipelineTier} size="sm" />
            </span>
          </div>
        </div>
        <div className="do-recruit-fit" aria-label={`Fit score: ${prospect.fit_score} out of 100`}>
          <TermTip term="recruit.fit">
            <span className="lbl">FIT</span>
          </TermTip>
          <span
            className="val mono"
            style={{
              fontSize: '1.1rem',
              color:
                prospect.fit_score >= 80
                  ? '#34d399'
                  : prospect.fit_score >= 65
                    ? '#f59e0b'
                    : '#f87171',
            }}
          >
            {prospect.fit_score}
            <span
              style={{ fontSize: '0.55rem', color: '#64748b', fontWeight: 400, marginLeft: '0.15rem' }}
            >
              /100
            </span>
          </span>
        </div>
      </div>

      <div className="do-recruit-meter">
        <div className="do-recruit-meter-bg">
          <div className="do-recruit-meter-fill" style={{ width: `${prospect.fit_score}%` }} />
        </div>
        <div className="do-recruit-meter-labels">
          <span>
            <TermTip term="recruit.fit">
              <span>{fitLabel.toUpperCase()}</span>
            </TermTip>
          </span>
          {typeof prospect.interest === 'number' && (
            <span className="mono">
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
        <div className="do-recruit-evidence">
          <span className="bar" />
          <span className="copy">{evidence.join(' · ')}</span>
        </div>
      )}
      {/* V24: what this prospect wants, graded from your real program with a
          receipt on hover. The dealbreaker (★) is hidden until you scout him —
          fail it and he never verbals. */}
      {prospect.motivations && prospect.motivations.length > 0 && (
        <div
          data-testid="prospect-motivations"
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', margin: '0.4rem 0 0' }}
        >
          {prospect.motivations.map((m) => (
            <span
              key={m.motivation}
              className="dm-badge dm-badge-slate"
              title={m.receipt}
              style={{ fontSize: '0.6rem' }}
            >
              {m.label} <strong>{m.letter}</strong>
            </span>
          ))}
          {prospect.dealbreaker ? (
            <span
              className={`dm-badge ${prospect.dealbreaker.veto ? 'dm-badge-orange' : 'dm-badge-violet'}`}
              title={prospect.dealbreaker.receipt}
              style={{ fontSize: '0.6rem' }}
            >
              ★ {prospect.dealbreaker.label} {prospect.dealbreaker.letter}
              {prospect.dealbreaker.veto ? " — WON'T VERBAL" : ''}
            </span>
          ) : (
            <span
              className="dm-badge dm-badge-slate"
              title="Scout this prospect to reveal what he cares about most"
              style={{ fontSize: '0.6rem', opacity: 0.6 }}
            >
              ★ Dealbreaker hidden — scout to reveal
            </span>
          )}
        </div>
      )}
      {prospect.active_promise && (
        <div
          data-testid="prospect-promise-chip"
          style={{
            display: 'flex',
            gap: '0.4rem',
            alignItems: 'baseline',
            margin: '0.35rem 0 0',
            fontSize: '0.68rem',
          }}
        >
          <span className={`dm-badge ${prospect.active_promise.status === 'broken' ? 'dm-badge-orange' : 'dm-badge-cyan'}`}>
            {prospect.active_promise.status === 'open'
              ? 'PROMISED'
              : prospect.active_promise.status === 'fulfilled'
                ? 'PROMISE KEPT'
                : 'PROMISE BROKEN'}
          </span>
          <span style={{ color: '#94a3b8' }}>
            {PROMISE_TYPE_LABELS[prospect.active_promise.promise_type] ?? prospect.active_promise.promise_type}
          </span>
        </div>
      )}
      <div className="do-recruit-actions">
        <button
          className="do-recruit-btn"
          disabled={loading || !canScout}
          onClick={() => runAction('scoutProspect', 'Scouted.', 'SCOUTED')}
          title={canScout ? 'Reveal more prospect detail' : 'No Scout slots remain this week'}
          type="button"
        >
          Scout
        </button>
        <button
          className="do-recruit-btn"
          disabled={loading || !canContact}
          onClick={() => runAction('contactProspect', 'Contact logged.', 'CONTACTED')}
          title={canContact ? 'Build recruit interest' : 'No Contact slots remain this week'}
          type="button"
        >
          Contact
        </button>
        <button
          className="do-recruit-btn primary"
          disabled={loading || !canVisit}
          onClick={() => runAction('visitProspect', 'Visit booked.', 'VISITED')}
          title={
            canVisit
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
          className="do-recruit-btn"
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
          style={{ cursor: 'pointer' }}
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

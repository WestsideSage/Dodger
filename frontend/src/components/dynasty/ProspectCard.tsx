import { useEffect, useRef, useState } from 'react';
import { dynastyApi } from '../../api/client';
import type { DynastyOfficeResponse, RecruitingStatus } from '../../types';
import { RecruitingBadge } from './RecruitingBadge';
import { TermTip, PipelineEmblem, KnownValue } from '../../legibility';
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
        setFeedbackMessage(error instanceof Error ? error.message : 'Action failed.');
        if (feedbackTimer.current !== null) clearTimeout(feedbackTimer.current);
        feedbackTimer.current = setTimeout(() => setFeedbackMessage(null), 3200);
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
        </div>
        <div
          aria-label="Card color key: green = Strong Fit, amber = Fair Fit, red = At Risk"
          style={{
            display: 'flex',
            gap: '0.75rem',
            marginTop: '0.3rem',
            fontSize: '0.55rem',
            color: '#64748b',
            letterSpacing: '0.04em',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ color: '#34d399' }}>● Strong Fit ≥80</span>
          <span style={{ color: '#f59e0b' }}>● Fair Fit 65–79</span>
          <span style={{ color: '#f87171' }}>● At Risk &lt;65</span>
        </div>
      </div>

      {evidence.length > 0 && (
        <div className="do-recruit-evidence">
          <span className="bar" />
          <span className="copy">{evidence.join(' · ')}</span>
        </div>
      )}
      {!prospect.scouted && (
        <p
          style={{
            margin: '0.25rem 0 0',
            fontSize: '0.6rem',
            color: '#64748b',
            lineHeight: 1.4,
          }}
        >
          Scout to narrow the OVR range and sharpen fit precision. Contact and visits build interest.
        </p>
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
      </div>
    </div>
  );
}

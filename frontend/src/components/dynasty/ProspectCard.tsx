import { useState } from 'react';
import { dynastyApi } from '../../api/client';
import type { DynastyOfficeResponse, RecruitingStatus } from '../../types';
import { RecruitingBadge } from './RecruitingBadge';

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

const archetypeBadge = (label: string) => {
  const normalized = label.toLowerCase();
  const tone =
    normalized.includes('sharpshooter') || normalized.includes('skirmisher')
      ? 'dm-badge-orange'
      : normalized.includes('net specialist')
        || normalized.includes('possession specialist')
        || normalized.includes('hit-and-run')
      ? 'dm-badge-violet'
      : 'dm-badge-cyan';
  return <span className={`dm-badge ${tone}`}>{label.toUpperCase()}</span>;
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
        setTimeout(() => setFeedbackMessage(null), 3200);
        onAction();
      })
      .catch((error) => {
        // Revert optimistic update on failure.
        setOptimisticStatus(previousOptimistic);
        setFeedbackTone('error');
        setFeedbackMessage(error instanceof Error ? error.message : 'Action failed.');
        setTimeout(() => setFeedbackMessage(null), 3200);
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
  const evidence = prospect.interest_evidence.filter(Boolean).slice(0, 2);

  return (
    <div className={`do-recruit fit-${fitTier}`} style={{ position: 'relative' }}>
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
          <div className="do-recruit-sub">
            <span>#{String(priority).padStart(2, '0')}</span>
            <span className="dot">·</span>
            <span>{prospect.hometown}</span>
            <span className="dot">·</span>
            {archetypeBadge(prospect.public_archetype || 'Balanced')}
            <span className="dot">·</span>
            <RecruitingBadge status={displayStatus} pending={pending} />
          </div>
        </div>
        <div className="do-recruit-fit">
          <span className="lbl">FIT</span>
          <span className="val mono">{prospect.fit_score}</span>
        </div>
      </div>

      <div className="do-recruit-meter">
        <div className="do-recruit-meter-bg">
          <div className="do-recruit-meter-fill" style={{ width: `${prospect.fit_score}%` }} />
        </div>
        <div className="do-recruit-meter-labels">
          <span>{fitLabel.toUpperCase()}</span>
          {typeof prospect.interest === 'number' && (
            <span className="mono">INT {prospect.interest}%</span>
          )}
          <span className="ovr mono">OVR {low}-{high}</span>
        </div>
      </div>

      {evidence.length > 0 && (
        <div className="do-recruit-evidence">
          <span className="bar" />
          <span className="copy">{evidence.join(' · ')}</span>
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
          title={canVisit ? 'Spend a visit slot' : 'No Visit slots remain this week'}
          type="button"
        >
          Visit
        </button>
      </div>
    </div>
  );
}

import type { RecruitingStatus } from '../../types';

const STATUS_LABELS: Record<RecruitingStatus, string> = {
  UNSCOUTED: 'Unscouted',
  SCOUTED: 'Scouted',
  CONTACTED: 'Contacted',
  VISITED: 'Visited',
  INTERESTED: 'Interested',
  LOCKED_OUT: 'Locked Out',
};

// Reuse the existing dm-badge tone palette from index.css.
const STATUS_TONES: Record<RecruitingStatus, string> = {
  UNSCOUTED: 'dm-badge-slate',
  SCOUTED: 'dm-badge-cyan',
  CONTACTED: 'dm-badge-amber',
  VISITED: 'dm-badge-violet',
  INTERESTED: 'dm-badge-emerald',
  LOCKED_OUT: 'dm-badge-rose',
};

export function RecruitingBadge({
  status,
  pending = false,
}: {
  status: RecruitingStatus;
  pending?: boolean;
}) {
  const tone = STATUS_TONES[status];
  const label = STATUS_LABELS[status];
  return (
    <span
      className={`dm-badge ${tone}`}
      data-testid={`recruiting-badge-${status}`}
      aria-label={`Recruiting status: ${label}${pending ? ' (saving)' : ''}`}
      title={`Recruiting status: ${label}`}
      style={pending ? { opacity: 0.6 } : undefined}
    >
      {label}
      {pending ? '…' : ''}
    </span>
  );
}

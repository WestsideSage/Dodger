import type { RecruitingStatus } from '../../types';
import styles from './RecruitingBadge.module.css';

const STATUS_LABELS: Record<RecruitingStatus, string> = {
  UNSCOUTED: 'Unscouted',
  SCOUTED: 'Scouted',
  CONTACTED: 'Contacted',
  VISITED: 'Visited',
  INTERESTED: 'Interested',
  LOCKED_OUT: 'Locked Out',
};

// Floodlight tone classes (5-color contract): positive engagement -> mint,
// locked-out -> dim/resolved, early states -> warm neutral.
const STATUS_TONES: Record<RecruitingStatus, string> = {
  UNSCOUTED: styles.toneUnscouted,
  SCOUTED: styles.toneScouted,
  CONTACTED: styles.toneContacted,
  VISITED: styles.toneVisited,
  INTERESTED: styles.toneInterested,
  LOCKED_OUT: styles.toneLockedOut,
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
      className={`${styles.badge} ${tone}${pending ? ` ${styles.pending}` : ''}`}
      data-testid={`recruiting-badge-${status}`}
      aria-label={`Recruiting status: ${label}${pending ? ' (saving)' : ''}`}
      title={`Recruiting status: ${label}`}
    >
      {label}
      {pending ? '…' : ''}
    </span>
  );
}

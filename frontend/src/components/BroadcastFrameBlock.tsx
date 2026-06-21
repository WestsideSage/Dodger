import type { BroadcastFrame, BroadcastTag } from '../types';
import styles from './BroadcastFrameBlock.module.css';

// Live / high-stakes tones get the single Volt "on air" accent; every other tone
// reads as a calm warm-neutral pill. Presentation only — tone never changes which
// proof-source a tag carries.
const LIVE_TONES = new Set(['title', 'playoff', 'rivalry']);
function isLiveTone(tone: string): boolean {
  return LIVE_TONES.has(tone);
}

function formatProofSource(source: string): string {
  let cleaned = source;
  if (cleaned.startsWith('record:')) {
    cleaned = cleaned.substring('record:'.length);
  }
  if (cleaned.startsWith('career:')) {
    cleaned = cleaned.substring('career:'.length);
  }
  cleaned = cleaned.replaceAll('_', ' ').replaceAll('-', ' ');
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function ProofRow({ label, source }: { label: string; source: string }) {
  return (
    <div className={styles.proofRow}>
      <span className={styles.proofLabel}>{label}</span>
      <code className={styles.proofSource}>{formatProofSource(source)}</code>
    </div>
  );
}

function FrameTag({ tag }: { tag: BroadcastTag }) {
  return (
    <span
      data-broadcast-proof-source={tag.proof_source}
      data-broadcast-tone={tag.tone}
      className={`${styles.tag} ${isLiveTone(tag.tone) ? styles.tagLive : styles.tagNeutral}`}
    >
      {tag.label}
    </span>
  );
}

export function BroadcastFrameBlock({
  frame,
  title = 'Broadcast Frame',
  compact = false,
}: {
  frame?: BroadcastFrame | null;
  title?: string;
  compact?: boolean;
}) {
  if (!frame) return null;
  const tags = [frame.stakes_tag, frame.rivalry_tag, frame.archetype_tag].filter(
    (tag): tag is BroadcastTag => Boolean(tag),
  );
  if (tags.length === 0 && !frame.historical_hook) return null;
  const proofRows = [
    ...tags.map(tag => ({ label: tag.label, source: tag.proof_source })),
    ...(frame.historical_hook
      ? [{ label: 'Historical hook', source: frame.historical_hook.proof_source }]
      : []),
  ];

  return (
    <section
      className="dm-panel"
      style={{
        padding: compact ? '0.75rem 0.9rem' : '0.9rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.65rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center' }}>
        <p className="dm-kicker" style={{ margin: 0 }}>{title}</p>
        <span className={styles.voiceSlot}>
          {frame.voice_slot.replace('broadcast.', '').replaceAll('_', ' ')}
        </span>
      </div>

      {tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
          {tags.map(tag => (
            <FrameTag key={`${tag.tone}-${tag.label}`} tag={tag} />
          ))}
        </div>
      )}

      {frame.historical_hook && (
        <p
          data-broadcast-proof-source={frame.historical_hook.proof_source}
          className={styles.hook}
        >
          {frame.historical_hook.text}
        </p>
      )}

      {proofRows.length > 0 && (
        <details>
          <summary
            data-testid="broadcast-proof-toggle"
            className={styles.evidenceToggle}
          >
            View evidence ⌄
          </summary>
          <div style={{ marginTop: '0.45rem' }}>
            {proofRows.map(row => (
              <ProofRow key={`${row.label}-${row.source}`} label={row.label} source={row.source} />
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

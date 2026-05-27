import type { BroadcastFrame, BroadcastTag } from '../types';

function toneAccent(tone: string): string {
  if (tone === 'title') return '#fbbf24';
  if (tone === 'playoff') return '#f97316';
  if (tone === 'rivalry') return '#ef4444';
  if (tone === 'trajectory') return '#22d3ee';
  if (tone === 'opening') return '#38bdf8';
  return '#94a3b8';
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
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: '0.75rem',
        padding: '0.3rem 0',
        borderBottom: '1px solid #0f172a',
        fontSize: '0.72rem',
      }}
    >
      <span style={{ color: '#cbd5e1' }}>{label}</span>
      <code style={{ color: '#64748b', fontSize: '0.7rem' }}>{formatProofSource(source)}</code>
    </div>
  );
}

function FrameTag({ tag }: { tag: BroadcastTag }) {
  return (
    <span
      data-broadcast-proof-source={tag.proof_source}
      style={{
        borderRadius: '999px',
        border: `1px solid ${toneAccent(tag.tone)}55`,
        background: `${toneAccent(tag.tone)}18`,
        color: toneAccent(tag.tone),
        padding: '0.22rem 0.6rem',
        fontSize: '0.68rem',
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}
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
        <span style={{ color: '#475569', fontSize: '0.68rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
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
          style={{ margin: 0, color: '#cbd5e1', fontSize: '0.82rem', lineHeight: 1.5 }}
        >
          {frame.historical_hook.text}
        </p>
      )}

      {proofRows.length > 0 && (
        <details>
          <summary
            data-testid="broadcast-proof-toggle"
            style={{ cursor: 'pointer', color: '#94a3b8', fontSize: '0.76rem' }}
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

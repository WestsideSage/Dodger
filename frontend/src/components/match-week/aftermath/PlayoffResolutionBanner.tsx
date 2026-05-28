import type { Aftermath } from '../../../types';

/**
 * Renders an explicit "you advanced / you were eliminated" banner at
 * the top of the aftermath flow when a playoff match needed a
 * tiebreaker. Reads `decided_by` directly — never derives from score.
 *
 * Task 1 of the 2026-05-27 rookie-run playtest-fixes plan. The single
 * most-cited trust break in the playtest was a tied 0-0 semifinal that
 * silently advanced by seed and jumped straight to offseason. This
 * component is the user-facing half of the fix.
 */
export function PlayoffResolutionBanner({
  resolution,
}: {
  resolution: NonNullable<Aftermath['playoff_resolution']>;
}) {
  if (resolution.decided_by === 'regulation') return null;

  const chip = resolution.decided_by === 'overtime' ? 'OVERTIME' : 'TIEBREAKER';
  const isAdvanced = resolution.player_outcome === 'advanced';
  const isEliminated = resolution.player_outcome === 'eliminated';

  let title: string;
  if (isAdvanced) {
    title = `Advanced — won in ${decidedByLabel(resolution.decided_by)}`;
  } else if (isEliminated) {
    title = `Eliminated — lost in ${decidedByLabel(resolution.decided_by)}`;
  } else {
    // AI-only match: still surface the resolution without addressing the player.
    title = `Decided in ${decidedByLabel(resolution.decided_by)}`;
  }

  const accent = isAdvanced
    ? { border: '#22c55e', glow: 'rgba(34,197,94,0.18)' }
    : isEliminated
      ? { border: '#ef4444', glow: 'rgba(239,68,68,0.18)' }
      : { border: '#22d3ee', glow: 'rgba(34,211,238,0.18)' };

  return (
    <section
      data-testid="playoff-resolution-banner"
      data-decided-by={resolution.decided_by}
      data-player-outcome={resolution.player_outcome ?? 'neutral'}
      style={{
        border: `1px solid ${accent.border}`,
        background: accent.glow,
        borderRadius: '8px',
        padding: '0.85rem 1rem',
        margin: '0 0 1rem 0',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.35rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <span
          style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            padding: '0.15rem 0.5rem',
            borderRadius: '3px',
            background: accent.border,
            color: '#0b1220',
          }}
        >
          {chip}
        </span>
        <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {resolution.stage}
        </span>
      </div>
      <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#f8fafc' }}>{title}</h3>
      <p style={{ margin: 0, fontSize: '0.85rem', color: '#cbd5f5', lineHeight: 1.4 }}>
        {resolution.narrative_note}
      </p>
    </section>
  );
}

function decidedByLabel(decidedBy: 'overtime' | 'seed_tiebreaker' | 'regulation'): string {
  if (decidedBy === 'overtime') return 'overtime';
  if (decidedBy === 'seed_tiebreaker') return 'the seed tiebreaker';
  return 'regulation';
}

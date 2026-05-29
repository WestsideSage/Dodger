import type { Aftermath } from '../../../types';

/**
 * One-screen send-off shown when the player's playoff run ends, before
 * the regular-season recap. Reads the backend ``elimination`` block
 * directly — opponent, final score, what ended the run, who carried the
 * match, and a one-line returning-core look-ahead. The player must click
 * Continue to proceed into the offseason.
 *
 * Task 9 of the 2026-05-28 multi-season playtest-fixes plan: the defeat
 * used to jump straight to the recap, wasting the emotional moment.
 */
export function EliminationCeremony({
  elimination,
  onContinue,
  isAdvancing,
}: {
  elimination: NonNullable<Aftermath['elimination']>;
  onContinue: () => void;
  isAdvancing?: boolean;
}) {
  const { stage, opponent_name, player_score, opponent_score, cause, contributors, returning } =
    elimination;

  return (
    <section
      data-testid="elimination-ceremony"
      style={{
        maxWidth: '640px',
        margin: '0 auto',
        padding: '2rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        textAlign: 'center',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: '#f87171',
            textTransform: 'uppercase',
          }}
        >
          {stage} · Eliminated
        </span>
        <h2 style={{ margin: 0, fontSize: '1.6rem', color: '#f8fafc' }}>Your season ends here.</h2>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
          fontFamily: 'var(--font-mono-data, monospace)',
        }}
      >
        <span style={{ fontSize: '2.4rem', fontWeight: 800, color: '#f87171' }}>{player_score}</span>
        <span style={{ fontSize: '1rem', color: '#64748b' }}>vs {opponent_name}</span>
        <span style={{ fontSize: '2.4rem', fontWeight: 800, color: '#f8fafc' }}>{opponent_score}</span>
      </div>

      <div
        style={{
          border: '1px solid #1e293b',
          background: '#0b1220',
          borderRadius: '8px',
          padding: '1rem',
          textAlign: 'left',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div>
          <div style={labelStyle}>What ended your run</div>
          <p style={{ margin: '0.35rem 0 0', color: '#e2e8f0', lineHeight: 1.5 }}>{cause}</p>
        </div>

        {contributors.length > 0 && (
          <div>
            <div style={labelStyle}>Who carried it</div>
            <ul style={{ margin: '0.35rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.3rem' }}>
              {contributors.map((c) => (
                <li
                  key={c.player_name}
                  style={{ display: 'flex', justifyContent: 'space-between', color: '#cbd5e1', fontSize: '0.85rem' }}
                >
                  <span>{c.player_name}</span>
                  <span style={{ fontFamily: 'var(--font-mono-data, monospace)', color: '#94a3b8' }}>
                    {c.score.toFixed(1)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {returning.length > 0 && (
          <div>
            <div style={labelStyle}>Returns next season</div>
            <p style={{ margin: '0.35rem 0 0', color: '#a5b4fc', fontSize: '0.85rem', lineHeight: 1.5 }}>
              {returning.join(' · ')}
            </p>
          </div>
        )}
      </div>

      <button
        type="button"
        className="dm-btn"
        onClick={onContinue}
        disabled={isAdvancing}
        data-testid="elimination-continue"
        style={{ alignSelf: 'center', minWidth: '180px' }}
      >
        {isAdvancing ? 'Advancing…' : 'Continue to offseason ▸'}
      </button>
    </section>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: '0.625rem',
  fontWeight: 900,
  letterSpacing: '0.08em',
  color: '#64748b',
  textTransform: 'uppercase',
};

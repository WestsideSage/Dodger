import type { Aftermath } from '../../../types';

/**
 * Celebration hero shown at the very top of the aftermath screen when
 * the player wins the title-clinching final. Reads the backend
 * ``championship`` block directly.
 *
 * Task 10 of the 2026-05-28 multi-season playtest-fixes plan: the title
 * win used to be undersold by the standard debrief, with the real
 * celebration buried behind an extra Continue into the offseason. This
 * makes the trophy moment the first thing the player sees.
 */
export function ChampionshipHero({
  championship,
}: {
  championship: NonNullable<Aftermath['championship']>;
}) {
  const { champion_name, opponent_name, player_score, opponent_score, decided_by } = championship;
  const how =
    decided_by === 'overtime'
      ? ' in overtime'
      : decided_by === 'seed_tiebreaker'
        ? ' on the tiebreaker'
        : '';

  return (
    <section
      data-testid="championship-hero"
      style={{
        border: '1px solid #fbbf24',
        background: 'linear-gradient(180deg, rgba(251,191,36,0.16), rgba(251,191,36,0.04))',
        borderRadius: '10px',
        padding: '1.5rem 1.25rem',
        margin: '0 0 1.25rem 0',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <span
        style={{
          fontSize: '0.7rem',
          fontWeight: 800,
          letterSpacing: '0.16em',
          color: '#fbbf24',
          textTransform: 'uppercase',
        }}
      >
        Champions
      </span>
      <h2 style={{ margin: 0, fontSize: '2rem', fontWeight: 800, color: '#fde68a', lineHeight: 1.15 }}>
        {champion_name}
      </h2>
      <p style={{ margin: 0, fontSize: '0.9rem', color: '#e2e8f0' }}>
        {player_score}–{opponent_score} over {opponent_name}
        {how} to take the title.
      </p>
    </section>
  );
}

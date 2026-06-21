import type { Aftermath } from '../../../types';
import styles from './aftermathCards.module.css';

/**
 * Shown on loss aftermath screens only. Renders up to three concrete
 * next steps (weakest position group, most-depleted starter, coolest
 * critical recruit) the backend ranked from existing engine values.
 *
 * Task 11 of the 2026-05-28 multi-season playtest-fixes plan: a tough
 * loss used to leave the player with no clear next move.
 */
const CATEGORY_ACCENT: Record<string, string> = {
  position_group: styles.improveItemGroup,
  condition: styles.improveItemCondition,
  recruit: styles.improveItemRecruit,
};

export function NextBestImprovementPanel({
  panel,
}: {
  panel: NonNullable<Aftermath['improvement_panel']>;
}) {
  if (panel.length === 0) return null;

  return (
    <section data-testid="next-best-improvement" className={styles.improvePanel}>
      <div className={styles.improveHead}>
        Next best improvement
        {/* Codex issue 6: this panel is computed at the final whistle and
            does not track later front-office work — say so instead of
            looking unaware of actions taken since. */}
        <span className={styles.improveNote}>— postgame read; desk work since then isn't reflected</span>
      </div>
      <div className={styles.improveList}>
        {panel.map((item) => (
          <div key={item.category} className={`${styles.improveItem}${CATEGORY_ACCENT[item.category] ? ` ${CATEGORY_ACCENT[item.category]}` : ''}`}>
            <div style={{ flex: 1 }}>
              <div className={styles.improveItemTitle}>{item.title}</div>
              <div className={styles.improveItemDetail}>{item.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

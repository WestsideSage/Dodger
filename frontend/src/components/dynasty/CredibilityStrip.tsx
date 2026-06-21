import { TermTip } from '../../legibility';
import type { DynastyOfficeResponse } from '../../types';
import styles from './CredibilityStrip.module.css';

type RecruitingCredibility = DynastyOfficeResponse['recruiting']['credibility'];

// Tick positions aligned to the real _grade() breakpoints in recruiting_office.py:
// F=0–39, D=40–54, C=55–69, B=70–84, A=85+.
// Each tick marks where a NEW grade begins. Track width = 100pts so % = breakpoint value.
const TIER_TICKS: Array<{ label: string; pct: number }> = [
  { label: 'F', pct: 0 },
  { label: 'D', pct: 40 },
  { label: 'C', pct: 55 },
  { label: 'B', pct: 70 },
  { label: 'A', pct: 85 },
];

// Which tier bracket does the score currently sit in?
// Grade breakpoints (recruiting_office.py _grade): F=0-39, D=40-54, C=55-69, B=70-84, A=85+.
function tierBracket(score: number): { label: string; prev: number; next: number } {
  if (score >= 85) return { label: 'Tier A · Max reach', prev: 85, next: 100 };
  if (score >= 70) return { label: 'Tier B · Toward A', prev: 70, next: 85 };
  if (score >= 55) return { label: 'Tier C · Toward B', prev: 55, next: 70 };
  if (score >= 40) return { label: 'Tier D · Toward C', prev: 40, next: 55 };
  return { label: 'Tier F · Toward D', prev: 0, next: 40 };
}

export function CredibilityStrip({
  credibility,
}: {
  credibility: RecruitingCredibility;
}) {
  const score = credibility.score;
  // Grade always read from the payload — no independent re-derivation that could drift.
  const grade = credibility.grade;
  const bracket = tierBracket(score);
  // Fill % is the score's position within the 0-100 track (one-to-one).
  const fillPct = Math.min(100, Math.max(0, score));

  return (
    <div className={styles.cred}>
      <div className={styles.letter} aria-hidden="true">
        <span className={styles.tier}>{grade}</span>
        <div className={styles.halo} />
      </div>

      <div className={styles.main}>
        <span className={styles.kicker}>
          <TermTip term="program.credibility">Program Credibility</TermTip>
        </span>
        <h2 className={styles.title}>
          Tier {grade} · Regional
        </h2>
        <p className={styles.blurb}>
          Your recruiting reputation. Higher credibility starts every prospect
          warmer, and that interest strengthens your contested Signing Day
          offer. It rises with wins, youth development, and your club's
          long-term <TermTip term="program.prestige">prestige</TermTip>.
        </p>

        <div className={styles.progress} role="group" aria-label={`Program credibility score ${score} of 100`}>
          <div className={styles.progressHead}>
            <span className={styles.lbl}>{bracket.label}</span>
            <span className={styles.val}>
              <b>{score}</b> <span className={styles.dim}>/ 100</span>
            </span>
          </div>
          <div className={styles.track}>
            <div className={styles.fill} style={{ width: `${fillPct}%` }}>
              <span className={styles.marker} />
            </div>
            {TIER_TICKS.map(({ label, pct }) => (
              <span
                key={label}
                className={styles.tick}
                style={{ left: `${pct}%` }}
                aria-label={`Tier ${label} threshold`}
              >
                <span className={styles.tickLbl}>{label}</span>
              </span>
            ))}
          </div>
        </div>

        <div className={styles.evidence} aria-label="Credibility factors">
          {credibility.evidence.map((item, index) => (
            <div key={`${index}-${item}`} className={styles.item}>
              <span className={styles.ix} aria-hidden="true">{String(index + 1).padStart(2, '0')}.{' '}</span>
              <span className="copy">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

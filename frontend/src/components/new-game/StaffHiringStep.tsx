import { useState, useEffect, useMemo } from 'react';
import { ActionButton } from '../../ui';
import { formatK } from '../../money';
import { saveApi } from '../../api/client';
import type { StaffCandidate, StartingStaffResponse } from '../../types';
import styles from './StaffHiringStep.module.css';

// V22 Phase 3 (owner: "up the stakes and add a budget component"): the
// create-a-club wizard hires its founding six department heads from a
// generated market under the starting budget. Every department offers a
// cheap journeyman, so filling all six can never soft-lock the step — the
// stakes are in the PAYROLL you commit, which the treasury pays every season.

const TIER_LABEL: Record<StaffCandidate['tier'], string> = {
  journeyman: 'Journeyman',
  solid: 'Solid',
  premium: 'Premium',
};

const TIER_TONE: Record<StaffCandidate['tier'], string> = {
  journeyman: styles.tierJourneyman,
  solid: styles.tierSolid,
  premium: styles.tierPremium,
};

function titleize(department: string): string {
  return department.charAt(0).toUpperCase() + department.slice(1);
}

export function StaffHiringStep({
  seed,
  choices,
  setChoices,
  onNext,
  onBack,
}: {
  /** The wizard's creation seed — the same pool the build POST validates. */
  seed: number;
  choices: Record<string, string>;
  setChoices: (next: Record<string, string>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [market, setMarket] = useState<StartingStaffResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    saveApi.startingStaff(seed)
      .then((d) => setMarket(d))
      .catch(err => setLoadError(err instanceof Error ? err.message : 'Failed to load the staff market'));
  }, [seed]);

  // Default every department to its cheapest candidate once the market loads
  // (guaranteed affordable), so the step starts valid and never blocks.
  useEffect(() => {
    if (!market) return;
    if (market.departments.every(dept => choices[dept])) return;
    const next: Record<string, string> = { ...choices };
    for (const dept of market.departments) {
      if (next[dept]) continue;
      const cheapest = market.candidates
        .filter(c => c.department === dept)
        .sort((a, b) => a.salary_k - b.salary_k)[0];
      if (cheapest) next[dept] = cheapest.candidate_id;
    }
    setChoices(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market]);

  const byId = useMemo(
    () => new Map((market?.candidates ?? []).map(c => [c.candidate_id, c])),
    [market],
  );
  const committedPayroll = useMemo(
    () =>
      Object.values(choices).reduce(
        (total, id) => total + (byId.get(id)?.salary_k ?? 0),
        0,
      ),
    [choices, byId],
  );
  const budget = market?.budget_k ?? 0;
  const openingTreasury = budget - committedPayroll;
  const allFilled = market ? market.departments.every(dept => choices[dept]) : false;
  const overBudget = committedPayroll > budget;

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <p className={styles.kicker}>Step 3 of 4</p>
        <h2 className={styles.title}>Hire Your Staff</h2>
        <p className={styles.intro}>
          One head per department. Their salaries become your annual payroll — what you
          don&apos;t commit opens the club treasury.
        </p>
      </div>

      {/* Budget bar: the step's one decision surface. */}
      {market && (
        <div
          data-testid="staff-budget-bar"
          className={`${styles.budgetBar} ${overBudget ? styles.budgetBarOver : ''}`.trim()}
        >
          <span>Budget <strong className={styles.amountValue}>{formatK(budget)}</strong></span>
          <span>
            Committed payroll{' '}
            <strong className={overBudget ? styles.amountOver : styles.amountPayroll}>
              {formatK(committedPayroll)}/season
            </strong>
          </span>
          <span>
            Opening treasury{' '}
            <strong className={openingTreasury < 0 ? styles.amountTreasuryNeg : styles.amountTreasury}>
              {formatK(openingTreasury)}
            </strong>
          </span>
          <span className={styles.budgetNote}>
            Mid-table season pays ≈ {formatK(market.mid_table_payout_k)} — a heavy payroll
            is a real squeeze if you finish low.
          </span>
        </div>
      )}

      {loadError && (
        <div className={styles.loadError}>
          {loadError}
        </div>
      )}
      {!market && !loadError && (
        <p className={styles.loadingText}>Opening the staff market...</p>
      )}

      {market && (
        <div data-testid="staff-dept-scroll" className={styles.deptScroll}>
          {market.departments.map(dept => {
            const options = market.candidates.filter(c => c.department === dept);
            const effect = options[0]?.effect_summary;
            return (
              <div key={dept}>
                <div className={styles.deptHead}>
                  <span className={styles.deptName}>
                    {titleize(dept)}
                  </span>
                  <span className={styles.deptEffect}>{effect}</span>
                </div>
                <div className={styles.candidateGrid}>
                  {options.map(candidate => {
                    const selected = choices[dept] === candidate.candidate_id;
                    return (
                      <button
                        key={candidate.candidate_id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        data-testid="staff-candidate-card"
                        onClick={() => setChoices({ ...choices, [dept]: candidate.candidate_id })}
                        className={`${styles.candidateCard} ${selected ? styles.candidateCardSelected : ''}`.trim()}
                      >
                        <span className={styles.candidateTop}>
                          <span className={`${styles.candidateName} ${selected ? styles.candidateNameSelected : ''}`.trim()}>
                            {candidate.name}
                          </span>
                          <span className={`${styles.tierLabel} ${TIER_TONE[candidate.tier]}`}>
                            {TIER_LABEL[candidate.tier]}
                          </span>
                        </span>
                        <span className={styles.candidateRatings}>
                          {candidate.rating_primary}/{candidate.rating_secondary} ratings ·{' '}
                          <strong className={styles.candidateSalary}>{formatK(candidate.salary_k)}/yr</strong>
                        </span>
                        {/* V22 Phase 4: the wired number this hire's rating
                            drives — the decision is about THIS. */}
                        {candidate.effect_detail && (
                          <span className={styles.candidateEffect}>
                            {candidate.effect_detail}
                          </span>
                        )}
                        <span className={styles.candidateVoice}>
                          “{candidate.voice}”
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {market && (
        <p className={styles.rules}>{market.rules}</p>
      )}

      <div className={styles.actionRow}>
        <ActionButton variant="secondary" onClick={onBack}>Back</ActionButton>
        <ActionButton
          variant="primary"
          onClick={onNext}
          disabled={!allFilled || overBudget}
        >
          {overBudget
            ? 'Over budget — cheapen a hire'
            : `Next: Recruit Roster (payroll ${formatK(committedPayroll)}/season)`}
        </ActionButton>
      </div>
    </div>
  );
}

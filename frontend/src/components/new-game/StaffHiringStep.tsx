import { useState, useEffect, useMemo } from 'react';
import { ActionButton } from '../ui';
import { formatK } from '../../money';
import { saveApi } from '../../api/client';
import type { StaffCandidate, StartingStaffResponse } from '../../types';

// V22 Phase 3 (owner: "up the stakes and add a budget component"): the
// create-a-club wizard hires its founding six department heads from a
// generated market under the starting budget. Every department offers a
// cheap journeyman, so filling all six can never soft-lock the step — the
// stakes are in the PAYROLL you commit, which the treasury pays every season.

const TIER_LABEL: Record<StaffCandidate['tier'], { label: string; color: string }> = {
  journeyman: { label: 'Journeyman', color: '#94a3b8' },
  solid: { label: 'Solid', color: '#22d3ee' },
  premium: { label: 'Premium', color: '#fbbf24' },
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
      <div>
        <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Step 3 of 4</p>
        <h2 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0, fontSize: '1.25rem' }}>
          Hire Your Staff
        </h2>
        <p style={{ margin: '0.375rem 0 0', fontSize: '0.8125rem', color: '#64748b' }}>
          One head per department. Their salaries become your annual payroll — what you
          don&apos;t commit opens the club treasury.
        </p>
      </div>

      {/* Budget bar: the step's one decision surface. */}
      {market && (
        <div
          data-testid="staff-budget-bar"
          style={{
            background: 'rgba(15,23,42,0.6)',
            border: `1px solid ${overBudget ? 'rgba(248,113,113,0.5)' : '#1e293b'}`,
            borderRadius: '6px',
            padding: '0.625rem 0.75rem',
            display: 'flex',
            gap: '1.25rem',
            flexWrap: 'wrap',
            fontSize: '0.78rem',
            color: '#cbd5e1',
          }}
        >
          <span>Budget <strong style={{ color: '#e2e8f0' }}>{formatK(budget)}</strong></span>
          <span>
            Committed payroll{' '}
            <strong style={{ color: overBudget ? '#f87171' : '#fbbf24' }}>
              {formatK(committedPayroll)}/season
            </strong>
          </span>
          <span>
            Opening treasury{' '}
            <strong style={{ color: openingTreasury < 0 ? '#f87171' : '#34d399' }}>
              {formatK(openingTreasury)}
            </strong>
          </span>
          <span style={{ color: '#64748b' }}>
            Mid-table season pays ≈ {formatK(market.mid_table_payout_k)} — a heavy payroll
            is a real squeeze if you finish low.
          </span>
        </div>
      )}

      {loadError && (
        <div style={{ padding: '0.75rem', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: '4px', color: '#fb7185', fontSize: '0.875rem' }}>
          {loadError}
        </div>
      )}
      {!market && !loadError && (
        <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Opening the staff market...</p>
      )}

      {market && (
        <div style={{ maxHeight: '380px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingRight: '0.25rem' }}>
          {market.departments.map(dept => {
            const options = market.candidates.filter(c => c.department === dept);
            const effect = options[0]?.effect_summary;
            return (
              <div key={dept}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.3rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#e2e8f0' }}>
                    {titleize(dept)}
                  </span>
                  <span style={{ fontSize: '0.66rem', color: '#64748b' }}>{effect}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.4rem' }}>
                  {options.map(candidate => {
                    const selected = choices[dept] === candidate.candidate_id;
                    const tier = TIER_LABEL[candidate.tier];
                    return (
                      <button
                        key={candidate.candidate_id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        data-testid="staff-candidate-card"
                        onClick={() => setChoices({ ...choices, [dept]: candidate.candidate_id })}
                        style={{
                          textAlign: 'left',
                          padding: '0.5rem 0.6rem',
                          background: selected ? 'rgba(34,211,238,0.07)' : '#0f172a',
                          border: selected ? '1px solid rgba(34,211,238,0.45)' : '1px solid #1e293b',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.2rem',
                        }}
                      >
                        <span style={{ display: 'flex', justifyContent: 'space-between', gap: '0.4rem', alignItems: 'baseline' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.8rem', color: selected ? '#67e8f9' : '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {candidate.name}
                          </span>
                          <span style={{ fontSize: '0.62rem', fontWeight: 800, color: tier.color, textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>
                            {tier.label}
                          </span>
                        </span>
                        <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                          {candidate.rating_primary}/{candidate.rating_secondary} ratings ·{' '}
                          <strong style={{ color: '#e2e8f0' }}>{formatK(candidate.salary_k)}/yr</strong>
                        </span>
                        {/* V22 Phase 4: the wired number this hire's rating
                            drives — the decision is about THIS. */}
                        {candidate.effect_detail && (
                          <span style={{ fontSize: '0.64rem', color: '#34d399', lineHeight: 1.35 }}>
                            {candidate.effect_detail}
                          </span>
                        )}
                        <span style={{ fontSize: '0.64rem', color: '#475569', fontStyle: 'italic', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
        <p style={{ margin: 0, fontSize: '0.7rem', color: '#64748b' }}>{market.rules}</p>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
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

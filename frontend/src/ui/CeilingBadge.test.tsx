import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CeilingBadge, CEILING_LADDER } from './CeilingBadge';

describe('CeilingBadge (gold ceiling ladder, §3.5)', () => {
  it('renders the grade text and forwards data-*/aria', () => {
    render(<CeilingBadge grade="A+" data-testid="cb" aria-label="ceiling A plus" />);
    const el = screen.getByTestId('cb');
    expect(el).toHaveTextContent('A+');
    expect(el).toHaveAttribute('aria-label', 'ceiling A plus');
  });
  it('maps brighter grades to higher glow tiers (monotonic ladder)', () => {
    const { rerender } = render(<CeilingBadge grade="A+" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g5/);
    rerender(<CeilingBadge grade="A" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g4/);
    rerender(<CeilingBadge grade="A-" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g3/);
    rerender(<CeilingBadge grade="B+" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g2/);
    rerender(<CeilingBadge grade="B" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g1/);
    rerender(<CeilingBadge grade="B-" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g1/);
    rerender(<CeilingBadge grade="C" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g0/);
  });
  it('exposes the ladder legend as the single reference key (7 rungs, ordered A+→C)', () => {
    expect(CEILING_LADDER.map((r) => r.grade)).toEqual(['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C']);
    // every rung names a glow tier; tiers never increase as the grade descends
    const tierNums = CEILING_LADDER.map((r) => Number(r.tier.replace('g', '')));
    for (let i = 1; i < tierNums.length; i += 1) {
      expect(tierNums[i]).toBeLessThanOrEqual(tierNums[i - 1]);
    }
  });
});

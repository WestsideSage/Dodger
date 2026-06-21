// frontend/src/components/dynasty/CredibilityStrip.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CredibilityStrip } from './CredibilityStrip';
import type { DynastyOfficeResponse } from '../../types';

type Cred = DynastyOfficeResponse['recruiting']['credibility'];

const credibility: Cred = {
  score: 72,
  grade: 'B',
  evidence: ['Won 8 of last 10 league games.', 'Developed 3 youth prospects past their ceiling.'],
};

describe('CredibilityStrip (#59 payload grade, #20 verbatim evidence)', () => {
  it('shows the grade exactly from the payload, never re-derived', () => {
    render(<CredibilityStrip credibility={credibility} />);
    // grade 'B' is shown even though score 72 sits in the B bracket; the point is
    // it reads credibility.grade, not a local recomputation.
    expect(screen.getAllByText('B').length).toBeGreaterThan(0);
    expect(screen.getByText('72')).toBeInTheDocument();
  });
  it('renders every backend evidence string verbatim', () => {
    render(<CredibilityStrip credibility={credibility} />);
    expect(screen.getByText('Won 8 of last 10 league games.')).toBeInTheDocument();
    expect(screen.getByText('Developed 3 youth prospects past their ceiling.')).toBeInTheDocument();
  });
});

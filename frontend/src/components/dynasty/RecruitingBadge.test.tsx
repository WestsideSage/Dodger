// frontend/src/components/dynasty/RecruitingBadge.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecruitingBadge } from './RecruitingBadge';

describe('RecruitingBadge', () => {
  it('renders the human label + provenance testid + aria for a status', () => {
    render(<RecruitingBadge status="INTERESTED" />);
    const el = screen.getByTestId('recruiting-badge-INTERESTED');
    expect(el).toHaveTextContent('Interested');
    expect(el).toHaveAttribute('aria-label', 'Recruiting status: Interested');
  });
  it('marks the pending (saving) state in the aria-label and appends an ellipsis', () => {
    render(<RecruitingBadge status="SCOUTED" pending />);
    const el = screen.getByTestId('recruiting-badge-SCOUTED');
    expect(el).toHaveAttribute('aria-label', 'Recruiting status: Scouted (saving)');
    expect(el).toHaveTextContent('Scouted…');
  });
});

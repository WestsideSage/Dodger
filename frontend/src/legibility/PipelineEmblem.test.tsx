import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PipelineEmblem } from './PipelineEmblem';

describe('PipelineEmblem (audit #26 pipeline vocabulary)', () => {
  it('labels tier 5 as Platinum (img role) and shows the numeral', () => {
    render(<PipelineEmblem tier={5} />);
    const emblem = screen.getByRole('img', { name: /Pipeline Tier 5 \(Platinum\)/ });
    expect(emblem).toHaveTextContent('5');
  });

  it('uses metal/league names, never potential or arc words', () => {
    render(<PipelineEmblem tier={3} />);
    const emblem = screen.getByRole('img', { name: /Pipeline Tier 3 \(Gold\)/ });
    expect(emblem.getAttribute('aria-label')).not.toMatch(/Elite|High-ceiling|arc/i);
  });
});

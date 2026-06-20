import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RatingBar } from './RatingBar';

describe('RatingBar shim', () => {
  it('renders the rounded value and a labelled explanation affordance', () => {
    render(<RatingBar rating={73.4} label="Catch" explanation="How often a catch lands." />);
    expect(screen.getByText('73')).toBeInTheDocument();
    const info = screen.getByTestId('rating-explanation');
    expect(info).toHaveAttribute('data-explanation-label', 'Catch');
    expect(info).toHaveAttribute('aria-label', expect.stringContaining('How often a catch lands.'));
  });
  it('renders without a label (value-left layout) and clamps to 0..100', () => {
    render(<RatingBar rating={150} />);
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});

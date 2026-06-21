import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatBar } from './StatBar';

describe('StatBar (glanceable rating, brightness = strength)', () => {
  it('renders the rounded value and the label, forwards data-*/title', () => {
    render(<StatBar label="ACC" value={73.4} title="Accuracy" data-testid="sb" />);
    const el = screen.getByTestId('sb');
    expect(el).toHaveTextContent('ACC');
    expect(el).toHaveTextContent('73');
    expect(el).toHaveAttribute('title', 'Accuracy');
  });
  it('assigns brightness tiers by strength', () => {
    const { rerender } = render(<StatBar label="X" value={90} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/elite/);
    rerender(<StatBar label="X" value={72} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/good/);
    rerender(<StatBar label="X" value={60} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/avg/);
    rerender(<StatBar label="X" value={40} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/poor/);
  });
  it('clamps the fill width to 0..100% via a custom property', () => {
    render(<StatBar label="X" value={150} data-testid="sb" />);
    const fill = screen.getByTestId('sb').querySelector('[data-statbar-fill]') as HTMLElement;
    expect(fill.style.getPropertyValue('--fill')).toBe('100%');
  });
});

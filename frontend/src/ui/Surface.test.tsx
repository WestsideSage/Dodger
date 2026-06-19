import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Surface, Card } from './Surface';

describe('Surface', () => {
  it('applies an elevation class and forwards data-*', () => {
    render(<Surface elevation={2} data-testid="s">x</Surface>);
    expect(screen.getByTestId('s').className).toMatch(/e2/);
  });
  it('Card is a padded surface that forwards role/aria', () => {
    render(<Card role="group" aria-label="card" data-testid="c">x</Card>);
    const el = screen.getByTestId('c');
    expect(el).toHaveAttribute('role', 'group');
    expect(el).toHaveAttribute('aria-label', 'card');
  });
});

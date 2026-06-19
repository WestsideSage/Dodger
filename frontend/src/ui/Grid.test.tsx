import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Grid } from './Grid';

describe('Grid', () => {
  it('sets the --grid-min custom property and forwards data-*', () => {
    render(<Grid min="200px" data-testid="g"><span>a</span></Grid>);
    const el = screen.getByTestId('g');
    expect(el.style.getPropertyValue('--grid-min')).toBe('200px');
  });
});

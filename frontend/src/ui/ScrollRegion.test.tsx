import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ScrollRegion } from './ScrollRegion';

describe('ScrollRegion', () => {
  it('applies maxHeight and forwards data-*', () => {
    render(<ScrollRegion maxHeight="200px" data-testid="r"><div>tall</div></ScrollRegion>);
    expect(screen.getByTestId('r').style.maxHeight).toBe('200px');
  });
});

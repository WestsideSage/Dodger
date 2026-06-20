import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ActionBar } from './ActionBar';

describe('ActionBar', () => {
  it('renders actions and forwards data-*', () => {
    render(<ActionBar data-testid="bar"><button>Next</button></ActionBar>);
    expect(screen.getByTestId('bar')).toHaveTextContent('Next');
  });
});

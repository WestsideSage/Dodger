import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Truncate } from './Truncate';

describe('Truncate', () => {
  it('renders children and forwards data-* + title', () => {
    render(<Truncate title="full" data-testid="t">A very long club name</Truncate>);
    const el = screen.getByTestId('t');
    expect(el).toHaveTextContent('A very long club name');
    expect(el).toHaveAttribute('title', 'full');
  });
  it('renders as the requested element', () => {
    render(<Truncate as="h3" data-testid="h">Heading</Truncate>);
    expect(screen.getByTestId('h').tagName).toBe('H3');
  });
});

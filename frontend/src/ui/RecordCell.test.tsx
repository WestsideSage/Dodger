import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecordCell } from './RecordCell';

describe('RecordCell', () => {
  it('renders an atomic W–L record', () => {
    render(<RecordCell wins={7} losses={2} data-testid="r" />);
    expect(screen.getByTestId('r')).toHaveTextContent('7–2');
  });
  it('includes draws when provided', () => {
    render(<RecordCell wins={7} losses={2} draws={1} data-testid="r" />);
    expect(screen.getByTestId('r')).toHaveTextContent('7–2–1');
  });
});

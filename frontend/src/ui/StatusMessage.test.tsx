import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusMessage } from './StatusMessage';

describe('StatusMessage shim', () => {
  it('derives role=alert for danger and warning tones', () => {
    const { rerender } = render(<StatusMessage title="Blocked" tone="danger">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Blocked');
    rerender(<StatusMessage title="Careful" tone="warning">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Careful');
  });
  it('derives role=status for calm tones and honors an explicit role', () => {
    const { rerender } = render(<StatusMessage title="Loading" tone="info">x</StatusMessage>);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    rerender(<StatusMessage title="Heads up" tone="info" role="alert">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Heads up');
  });
  it('sets aria-live matching the resolved role', () => {
    render(<StatusMessage title="Blocked" tone="danger">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive');
  });
});

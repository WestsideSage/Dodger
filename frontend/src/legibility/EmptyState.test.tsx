import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EmptyState } from './EmptyState';

describe('EmptyState (audit #31 truth surface)', () => {
  it('renders a status region with the given title and body', () => {
    render(<EmptyState title="No prospect movement" body="Nothing changed this week." />);
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('No prospect movement');
    expect(region).toHaveTextContent('Nothing changed this week.');
  });

  it('renders an optional decorative icon as aria-hidden', () => {
    render(<EmptyState title="t" body="b" icon={<span>★</span>} />);
    expect(screen.getByText('★').closest('[aria-hidden="true"]')).not.toBeNull();
  });
});

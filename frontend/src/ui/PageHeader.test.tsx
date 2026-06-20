import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PageHeader } from './PageHeader';

describe('PageHeader shim', () => {
  it('renders title, optional eyebrow/description/actions/stats', () => {
    render(
      <PageHeader
        eyebrow="WAR ROOM"
        title="Command Center"
        description="Plan the week."
        actions={<button>Act</button>}
        stats={<span>3 wins</span>}
      />,
    );
    expect(screen.getByRole('heading', { name: 'Command Center' })).toBeInTheDocument();
    expect(screen.getByText('WAR ROOM')).toBeInTheDocument();
    expect(screen.getByText('Plan the week.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Act' })).toBeInTheDocument();
    expect(screen.getByText('3 wins')).toBeInTheDocument();
  });
});

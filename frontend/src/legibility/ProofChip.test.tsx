import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ProofChip } from './ProofChip';

describe('ProofChip (audit #20 verbatim receipt, #30 provenance)', () => {
  it('renders the source string VERBATIM in the popover when opened', async () => {
    const SOURCE = 'record: 7-2 vs Granite City (Week 4)';
    render(<ProofChip label="WHY" source={SOURCE} />);
    await userEvent.click(screen.getByRole('button', { name: /WHY/ }));
    expect(screen.getByRole('note')).toHaveTextContent(SOURCE);
  });

  it('forwards caller data-* provenance onto the trigger (anti-strip)', () => {
    render(
      <ProofChip
        label="WHY"
        source="x"
        data-broadcast-proof-source="career"
        data-testid="chip"
      />,
    );
    const trigger = screen.getByTestId('chip');
    expect(trigger).toHaveAttribute('data-broadcast-proof-source', 'career');
  });

  it('toggles the popover open/closed and is closed by default', async () => {
    render(<ProofChip label="WHY" source="receipt body" />);
    expect(screen.queryByText('receipt body')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /WHY/ }));
    expect(screen.getByText('receipt body')).toBeInTheDocument();
  });
});

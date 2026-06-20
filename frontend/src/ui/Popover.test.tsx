import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Popover } from './Popover';

describe('Popover', () => {
  it('renders content in a portal when open and forwards data-*/role', () => {
    render(
      <Popover open anchor={<button>open</button>} data-testid="pop" role="tooltip">
        receipt body
      </Popover>,
    );
    const pop = screen.getByTestId('pop');
    expect(pop).toHaveTextContent('receipt body');
    expect(pop).toHaveAttribute('role', 'tooltip');
  });
  it('renders nothing when closed', () => {
    render(<Popover open={false} anchor={<button>open</button>}>hidden</Popover>);
    expect(screen.queryByText('hidden')).not.toBeInTheDocument();
  });
});

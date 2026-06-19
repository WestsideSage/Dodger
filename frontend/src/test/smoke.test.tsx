import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

function Hello() { return <p>floodlight</p>; }

describe('test harness', () => {
  it('renders a component', () => {
    render(<Hello />);
    expect(screen.getByText('floodlight')).toBeInTheDocument();
  });
});

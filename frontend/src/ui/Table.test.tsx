import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Table } from './Table';

describe('Table', () => {
  it('applies density class and forwards data-* (anti-strip)', () => {
    render(
      <Table density="compact" data-testid="tbl">
        <tbody><tr><td>Granite City Hammers</td></tr></tbody>
      </Table>,
    );
    const t = screen.getByTestId('tbl');
    expect(t.tagName).toBe('TABLE');
    expect(t.className).toMatch(/compact/);
    expect(t).toHaveTextContent('Granite City Hammers');
  });
});

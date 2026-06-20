import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Tag } from './Tag';

describe('Tag', () => {
  it('applies the tone class and forwards data-*', () => {
    render(<Tag tone="verified" data-testid="t">Healthy</Tag>);
    expect(screen.getByTestId('t').className).toMatch(/verified/);
  });
});

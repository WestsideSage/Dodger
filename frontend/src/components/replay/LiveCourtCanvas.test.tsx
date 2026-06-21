import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LiveCourtCanvas } from './LiveCourtCanvas';

const reg = new Map([
  ['p1', { id: 'p1', name: 'A One', label: 'A. ONE', clubId: 'aurora' }],
  ['p2', { id: 'p2', name: 'B Two', label: 'B. TWO', clubId: 'granite' }],
]);

describe('LiveCourtCanvas (net-new SVG)', () => {
  it('renders an SVG court with one token per registered player', () => {
    render(
      <LiveCourtCanvas
        homeIds={['p1']}
        awayIds={['p2']}
        playerRegistry={reg}
        eliminatedIds={new Set()}
        throwerId={null}
        targetId={null}
        activeResolution={null}
      />,
    );
    const svg = screen.getByLabelText(/live .*court/i);
    expect(svg.tagName.toLowerCase()).toBe('svg');
    expect(svg.querySelectorAll('[data-player-token]').length).toBe(2);
  });

  it('marks an eliminated player as extinguished (data-extinguished="true")', () => {
    render(
      <LiveCourtCanvas
        homeIds={['p1']}
        awayIds={['p2']}
        playerRegistry={reg}
        eliminatedIds={new Set(['p2'])}
        throwerId={null}
        targetId={null}
        activeResolution={null}
      />,
    );
    const tok = document.querySelector('[data-player-token="p2"]');
    expect(tok).toHaveAttribute('data-extinguished', 'true');
    const live = document.querySelector('[data-player-token="p1"]');
    expect(live).toHaveAttribute('data-extinguished', 'false');
  });

  it('draws a throw arc only when both thrower and target are present', () => {
    const { rerender } = render(
      <LiveCourtCanvas
        homeIds={['p1']}
        awayIds={['p2']}
        playerRegistry={reg}
        eliminatedIds={new Set()}
        throwerId={null}
        targetId={null}
        activeResolution={null}
      />,
    );
    expect(document.querySelector('[data-throw-arc]')).toBeNull();
    rerender(
      <LiveCourtCanvas
        homeIds={['p1']}
        awayIds={['p2']}
        playerRegistry={reg}
        eliminatedIds={new Set()}
        throwerId="p1"
        targetId="p2"
        activeResolution="eliminated"
      />,
    );
    expect(document.querySelector('[data-throw-arc]')).not.toBeNull();
  });

  it('honest NO-DATA fallback when there are no players', () => {
    render(
      <LiveCourtCanvas
        homeIds={[]}
        awayIds={[]}
        playerRegistry={new Map()}
        eliminatedIds={new Set()}
        throwerId={null}
        targetId={null}
        activeResolution={null}
      />,
    );
    expect(screen.getByText(/no live court/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/live .*court/i)).not.toBeInTheDocument();
  });

  it('scales to any side count (no 6-player assumption)', () => {
    const big = new Map(reg);
    ['p3', 'p4', 'p5'].forEach((id) => big.set(id, { id, name: id, label: id, clubId: 'aurora' }));
    render(
      <LiveCourtCanvas
        homeIds={['p1', 'p3', 'p4', 'p5']}
        awayIds={['p2']}
        playerRegistry={big}
        eliminatedIds={new Set()}
        throwerId={null}
        targetId={null}
        activeResolution={null}
      />,
    );
    const svg = screen.getByLabelText(/live .*court/i);
    expect(svg.querySelectorAll('[data-player-token]').length).toBe(5);
  });
});

import { render } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { ComponentProps } from 'react';
import type { MatchWeekMountProps } from './shell/appContracts';

// Mock the data hook + command API so MatchWeek mounts without real fetches.
vi.mock('../hooks/useApiResource', () => ({
  useApiResource: () => ({
    data: null,
    setData: vi.fn(),
    error: null,
    setError: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
  }),
}));
vi.mock('../api/client', () => ({
  commandApi: {
    center: vi.fn().mockResolvedValue(null),
    savePlan: vi.fn(),
    simulate: vi.fn(),
    replay: vi.fn().mockResolvedValue(null),
    highlights: vi.fn().mockResolvedValue({ beats: [] }),
    fastForward: vi.fn(),
    scoutOpponent: vi.fn(),
    confirmLineup: vi.fn(),
    skipSeasonPreview: vi.fn(),
  },
}));

import { MatchWeek, isNavClick } from './MatchWeek';
import { NAV_RAIL_ATTR } from './shell/appContracts';

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('MatchWeek nav reveal-skip + mount contract', () => {
  it('mount props are assignable to the Phase-1 MatchWeekMountProps contract (compile-time)', () => {
    const _props: MatchWeekMountProps = {} as ComponentProps<typeof MatchWeek>;
    void _props;
    expect(true).toBe(true);
  });

  it('isNavClick returns true inside [data-nav-rail], false otherwise', () => {
    const rail = document.createElement('aside');
    rail.setAttribute(NAV_RAIL_ATTR, '');
    const inner = document.createElement('button');
    rail.appendChild(inner);
    document.body.appendChild(rail);

    expect(isNavClick(inner, NAV_RAIL_ATTR)).toBe(true);

    const outside = document.createElement('button');
    document.body.appendChild(outside);
    expect(isNavClick(outside, NAV_RAIL_ATTR)).toBe(false);
    expect(isNavClick(null, NAV_RAIL_ATTR)).toBe(false);

    document.body.removeChild(rail);
    document.body.removeChild(outside);
  });

  it('NAV_RAIL_ATTR is the published data-nav-rail contract name', () => {
    expect(NAV_RAIL_ATTR).toBe('data-nav-rail');
  });

  it('the click skip handler is wired on window in post-sim mode', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    render(<MatchWeek mode="post-sim" persistedResult={null} />);
    expect(addSpy.mock.calls.some(([type]) => type === 'click')).toBe(true);
    addSpy.mockRestore();
  });
});

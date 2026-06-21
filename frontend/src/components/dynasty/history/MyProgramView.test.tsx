// frontend/src/components/dynasty/history/MyProgramView.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MyProgramView } from './MyProgramView';

const useApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({ useApiResource: (...a: unknown[]) => useApiResource(...a) }));

function programData(overrides: Record<string, unknown> = {}) {
  return {
    club_id: 'hammers',
    hero: {
      season_1: { season_label: 'season_1', wins: 6, losses: 4, draws: 0 },
      current: { season_label: 'season_3', wins: 1, losses: 0, draws: 0 },
      all_time: { wins: 18, losses: 10, draws: 2, seasons: 3 },
    },
    timeline: [],
    alumni: [],
    banners: [],
    ...overrides,
  };
}

describe('MyProgramView (#60 all-time label, #97 isSelf)', () => {
  it('#60: labels the record "All-Time Record" when hero.all_time is present', () => {
    useApiResource.mockReturnValue({ data: programData(), error: null, loading: false });
    render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText('All-Time Record')).toBeInTheDocument();
    expect(screen.getByText('18-10-2')).toBeInTheDocument();
  });
  it('#60: falls back to "Latest Season Record" when all_time is absent', () => {
    const d = programData();
    delete (d.hero as Record<string, unknown>).all_time;
    useApiResource.mockReturnValue({ data: d, error: null, loading: false });
    render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText('Latest Season Record')).toBeInTheDocument();
  });
  it('#97: shows "Your first alumni season is ahead" only when isSelf', () => {
    useApiResource.mockReturnValue({ data: programData(), error: null, loading: false });
    const { rerender } = render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText(/Your first alumni season is ahead/)).toBeInTheDocument();
    rerender(<MyProgramView clubId="rivals" isSelf={false} />);
    expect(screen.getByText(/No departed players yet/)).toBeInTheDocument();
  });
});

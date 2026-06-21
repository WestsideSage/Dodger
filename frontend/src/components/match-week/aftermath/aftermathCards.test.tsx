import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComebackCard } from './ComebackCard';
import { KeyPlayersPanel } from './KeyPlayersPanel';
import { ProgramStatusStrip } from '../ProgramStatusStrip';

// ProgramStatusStrip fetches from /api/standings via useApiResource; mock it.
vi.mock('../../../hooks/useApiResource', () => ({
  useApiResource: vi.fn(),
}));
import { useApiResource } from '../../../hooks/useApiResource';

const mockResource = (data: unknown) =>
  (useApiResource as ReturnType<typeof vi.fn>).mockReturnValue({
    data,
    loading: false,
    error: null,
    setData: vi.fn(),
    setError: vi.fn(),
    setLoading: vi.fn(),
  });

describe('aftermath card truth (#5, #48, #50, #35)', () => {
  it('#5 (official_foam career): differential shown is game_point_differential, NOT elimination_differential', () => {
    // ProgramStatusStrip.tsx:12-14: is_official_career → strapDiff = game_point_differential
    mockResource({
      is_official_career: true,
      standings: [
        {
          is_user_club: true,
          wins: 5,
          losses: 2,
          draws: 1,
          points: 16,
          game_point_differential: 12,
          elimination_differential: 4,
        },
      ],
    });
    render(<ProgramStatusStrip />);
    expect(screen.getByText(/\+12 diff/)).toBeInTheDocument();
    expect(screen.queryByText(/\+4 diff/)).not.toBeInTheDocument();
  });

  it('#5 (legacy career): differential shown is elimination_differential, NOT game_point_differential', () => {
    mockResource({
      is_official_career: false,
      standings: [
        {
          is_user_club: true,
          wins: 3,
          losses: 4,
          draws: 0,
          points: 9,
          game_point_differential: 12,
          elimination_differential: 4,
        },
      ],
    });
    render(<ProgramStatusStrip />);
    expect(screen.getByText(/\+4 diff/)).toBeInTheDocument();
    expect(screen.queryByText(/\+12 diff/)).not.toBeInTheDocument();
  });

  it('#48: ComebackCard self-suppresses on a shutout', () => {
    const { container } = render(
      <ComebackCard text="Clawed it back from 0-3." narrativeBeats={{ was_shutout: true, largest_deficit: 3 }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('#48: ComebackCard self-suppresses when the team never trailed', () => {
    const { container } = render(
      <ComebackCard text="Never trailed." narrativeBeats={{ was_shutout: false, largest_deficit: 0 }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('#48: ComebackCard renders when there was a real comeback', () => {
    render(<ComebackCard text="Erased a 4-point deficit." narrativeBeats={{ was_shutout: false, largest_deficit: 4 }} />);
    expect(screen.getByTestId('comeback-card')).toBeInTheDocument();
  });

  it('#50/#35: KeyPlayersPanel shows an honest fallback when no performers', () => {
    render(<KeyPlayersPanel performers={[]} playerClubName="Aurora" />);
    expect(screen.getByText(/No standout performances recorded/i)).toBeInTheDocument();
  });
});

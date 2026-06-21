import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecordsRatified, HallOfFameInduction } from './StructuredOffseasonBeats';

function recordsBeat(payload: Record<string, unknown>) {
  return { key: 'records_ratified', beat_index: 7, total_beats: 9, title: 'Records', can_advance: true, payload } as never;
}

function record(overrides: Record<string, unknown> = {}) {
  return {
    is_my_club: true, record_type: 'most_elims', proof_source: 'record:most_elims',
    holder_name: 'Star', previous_value: 100, new_value: 120, is_new_holder: true,
    ...overrides,
  };
}

describe('RecordsRatified (#70 tiering / #35 empty / proof-source)', () => {
  it('#35: records-book-empty shows the honest book-empty message', () => {
    render(<RecordsRatified beat={recordsBeat({ records: [], records_book_empty: true })} onComplete={() => {}} />);
    expect(screen.getByText(/record book is empty/i)).toBeInTheDocument();
  });

  it('#35: my-club-empty-but-league-has offers a one-tap path to League scope (no dead end)', () => {
    render(<RecordsRatified beat={recordsBeat({
      records: [record({ is_my_club: false })],
      records_book_empty: false,
    })} onComplete={() => {}} />);
    // default scope = League here (no my-club records), so the league record renders
    expect(screen.getByTestId('record-milestone-card')).toBeInTheDocument();
  });

  it('keeps data-broadcast-proof-source provenance on milestone cards', () => {
    const { container } = render(<RecordsRatified beat={recordsBeat({
      records: [record({ is_my_club: true })],
      records_book_empty: false,
    })} onComplete={() => {}} />);
    expect(container.querySelector('[data-broadcast-proof-source]')).not.toBeNull();
  });

  it('#71: record values render integerized (zero-floats)', () => {
    render(<RecordsRatified beat={recordsBeat({
      records: [record({ previous_value: 100, new_value: 120 })],
      records_book_empty: false,
    })} onComplete={() => {}} />);
    expect(screen.getByText('120')).toBeInTheDocument();
  });
});

describe('HallOfFameInduction (#35 empty / proof-source)', () => {
  it('shows the honest no-inductees line when the class is empty', () => {
    render(<HallOfFameInduction beat={{ key: 'hof_induction', beat_index: 8, total_beats: 9, title: 'HoF', can_advance: true, payload: { inductees: [] } } as never} onComplete={() => {}} />);
    expect(screen.getByText(/No new inductees/i)).toBeInTheDocument();
  });
});

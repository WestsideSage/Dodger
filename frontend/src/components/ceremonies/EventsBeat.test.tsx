import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EventsBeat } from './EventsBeat';

function eventsBeat(events: unknown[]) {
  return { key: 'events', beat_index: 3, total_beats: 9, payload: { events } } as never;
}

describe('EventsBeat (#35 honest empty state)', () => {
  it('shows the honest no-events line when nothing resolved', () => {
    render(<EventsBeat beat={eventsBeat([])} onComplete={() => {}} />);
    expect(screen.getByText(/No events resolved this season/i)).toBeInTheDocument();
  });
});

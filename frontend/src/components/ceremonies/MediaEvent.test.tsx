import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MediaEvent } from './MediaEvent';

function mediaBeat(payload: Record<string, unknown>) {
  return { key: 'media_event', beat_index: 5, total_beats: 9, title: 'Media Moment', payload } as never;
}

describe('MediaEvent (#31 honest null-vs-zero)', () => {
  it('renders the honest quiet-cycle line when there is no event and nothing committed', () => {
    render(<MediaEvent beat={mediaBeat({ event: null, committed: false, result: null })} onChoose={() => {}} onComplete={() => {}} />);
    expect(screen.queryByTestId('media-event')).not.toBeInTheDocument();
    expect(screen.queryByTestId('media-result')).not.toBeInTheDocument();
    expect(screen.getByText(/Quiet news cycle/i)).toBeInTheDocument();
  });

  it('renders the verbatim committed receipt (no re-derivation)', () => {
    render(<MediaEvent beat={mediaBeat({ committed: true, result: { receipt: '+3 fans, +1 prestige' }, event: null })} onChoose={() => {}} onComplete={() => {}} />);
    expect(screen.getByTestId('media-result')).toHaveTextContent('+3 fans, +1 prestige');
  });

  it('latches the chosen option with aria-pressed (selected-state hook survives)', async () => {
    const userEvent = (await import('@testing-library/user-event')).default;
    render(<MediaEvent beat={mediaBeat({
      committed: false, result: null,
      event: { prompt: 'Speak?', options: [{ key: 'a', label: 'Yes', fans: 3, prestige: 0, credibility: 0 }] },
    })} onChoose={() => {}} onComplete={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'Choose' }));
    expect(screen.getByText('Selected ✓')).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RookieClassPreview } from './RookieClassPreview';

// rookie_class_preview reads class_size, top_prospects (count), free_agents
// (count), archetypes[], storylines[], ceiling_prospects (count) — verified
// against RookieClassPreview.tsx.
function rookieBeat(payload: Record<string, unknown>) {
  return {
    key: 'rookie_class_preview', beat_index: 6, total_beats: 9,
    payload: { class_size: 0, top_prospects: 0, free_agents: 0, archetypes: [], storylines: [], ceiling_prospects: 0, ...payload },
  } as never;
}

describe('RookieClassPreview (#31 honest upside)', () => {
  it('renders the screen and does not fabricate upside when class is empty', () => {
    render(<RookieClassPreview beat={rookieBeat({})} onComplete={() => {}} />);
    expect(screen.getByTestId('offseason-rookie-preview')).toBeInTheDocument();
    // qualityPct is 0 when class_size is 0 — no fabricated percentage
    expect(screen.queryByText('NaN%')).not.toBeInTheDocument();
  });

  it('reports honest upside when ceiling prospects exist', () => {
    render(<RookieClassPreview beat={rookieBeat({ class_size: 10, ceiling_prospects: 2, top_prospects: 0 })} onComplete={() => {}} />);
    expect(screen.getByText(/2 of 10 rookies scout a ceiling of 70\+ OVR/)).toBeInTheDocument();
    expect(screen.getByText('20% of the class')).toBeInTheDocument();
  });
});

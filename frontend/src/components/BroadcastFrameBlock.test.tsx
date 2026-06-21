import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BroadcastFrameBlock } from './BroadcastFrameBlock';
import type { BroadcastFrame } from '../types';

const frame: BroadcastFrame = {
  stakes_tag: { label: 'Title Decider', tone: 'title', proof_source: 'record:title_race' },
  rivalry_tag: { label: 'Coastal Derby', tone: 'rivalry', proof_source: 'record:rivalry_series' },
  archetype_tag: { label: 'Up-and-comer', tone: 'trajectory', proof_source: 'career:trajectory' },
  historical_hook: { text: 'First meeting since the Worlds final.', proof_source: 'record:worlds_final' },
  voice_slot: 'broadcast.lead_caller',
};

describe('BroadcastFrameBlock (truth-bearing; reskin preserves proof hooks)', () => {
  it('preserves every data-broadcast-proof-source hook after the token reskin', () => {
    const { container } = render(<BroadcastFrameBlock frame={frame} />);
    const sources = Array.from(container.querySelectorAll('[data-broadcast-proof-source]')).map(
      el => el.getAttribute('data-broadcast-proof-source'),
    );
    expect(sources).toContain('record:title_race');
    expect(sources).toContain('record:rivalry_series');
    expect(sources).toContain('career:trajectory');
    expect(sources).toContain('record:worlds_final');
  });

  it('keeps the evidence toggle and renders each proof row source', () => {
    render(<BroadcastFrameBlock frame={frame} />);
    expect(screen.getByTestId('broadcast-proof-toggle')).toBeInTheDocument();
    // formatProofSource strips the record:/career: prefix and humanizes.
    expect(screen.getByText('Title race')).toBeInTheDocument();
    expect(screen.getByText('Trajectory')).toBeInTheDocument();
  });

  it('tags carry data-broadcast-tone so live (Volt) vs neutral is derivable, not raw color', () => {
    const { container } = render(<BroadcastFrameBlock frame={frame} />);
    const tones = Array.from(container.querySelectorAll('[data-broadcast-tone]')).map(el =>
      el.getAttribute('data-broadcast-tone'),
    );
    expect(tones).toEqual(expect.arrayContaining(['title', 'rivalry', 'trajectory']));
    // No inline style carrying a raw hex remains on the tags.
    container.querySelectorAll('[data-broadcast-tone]').forEach(el => {
      expect(el.getAttribute('style')).toBeNull();
    });
  });

  it('returns null when there is nothing to broadcast', () => {
    const { container } = render(
      <BroadcastFrameBlock frame={{ voice_slot: 'broadcast.lead_caller' }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

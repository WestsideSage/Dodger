import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeAll, vi } from 'vitest';
import { WorldsCrowning } from './WorldsCrowning';

// CeremonyShell's staged-reveal effect calls window.matchMedia (reduced-motion
// check) when stages > 0. jsdom doesn't implement it, so stub a stable match.
beforeAll(() => {
  if (!window.matchMedia) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as never;
  }
});

function crownBeat(payload: { champion_name: string; is_first: boolean; season_id: string }) {
  return {
    key: 'worlds_champion',
    beat_index: 5,
    total_beats: 9,
    title: 'Worlds Champions',
    body: '',
    payload,
  } as never;
}

describe('WorldsCrowning (Floodlight reskin — gold = the one legit championship use)', () => {
  it('first crown renders the staged reveal with the champion name (stage 0 visible)', () => {
    render(
      <WorldsCrowning
        beat={crownBeat({ champion_name: 'Granite City', is_first: true, season_id: 'Season 6' })}
        onComplete={() => {}}
      />,
    );
    // CeremonyShell renders stage 0 immediately; the staged-reveal hook is present.
    expect(screen.getByTestId('worlds-crown-stage-0')).toBeInTheDocument();
    expect(screen.getByText('The World Stage')).toBeInTheDocument();
  });

  it('defending champion renders the quiet single-stage retained beat', () => {
    render(
      <WorldsCrowning
        beat={crownBeat({ champion_name: 'Granite City', is_first: false, season_id: 'Season 7' })}
        onComplete={() => {}}
      />,
    );
    expect(screen.getByTestId('worlds-defending-stage')).toBeInTheDocument();
    expect(screen.getByText('Granite City')).toBeInTheDocument();
    expect(screen.getByText(/Retained the Worlds title/i)).toBeInTheDocument();
  });

  it('no longer carries inline color literals — color goes through token classes', () => {
    const { container } = render(
      <WorldsCrowning
        beat={crownBeat({ champion_name: 'Granite City', is_first: true, season_id: 'Season 6' })}
        onComplete={() => {}}
      />,
    );
    // The champion kicker moved from the global `.champion-kicker` class to
    // ceremonies/ceremony.module.css (CSS-Modules hash keeps the name as a
    // substring), and carries NO inline style attribute with a raw hex.
    const kicker = container.querySelector('[class*="champion-kicker"]');
    expect(kicker).not.toBeNull();
    expect(kicker!.getAttribute('style')).toBeNull();
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeAll, vi } from 'vitest';
import { SigningDay, AwardsNight } from './Ceremonies';

// CeremonyShell reads window.matchMedia (reduced-motion) inside its staged-reveal
// effect; jsdom doesn't provide it. AwardsNight drives staged reveals, so stub it.
beforeAll(() => {
  if (!window.matchMedia) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: true, media: query, onchange: null,
      addListener: vi.fn(), removeListener: vi.fn(),
      addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;
  }
});

function signingBeat(payload: Record<string, unknown>) {
  return {
    key: 'recruitment', beat_index: 8, total_beats: 9, title: 'Class Report',
    payload: { signed_count: 2, signing_limit: 3, signings: [], other_signings: [], ...payload },
  } as never;
}

describe('SigningDay (#67 signed_count single-source / #68 scope labels)', () => {
  it('#67: the "you signed" headline reads signed_count even when zero cards were recorded', () => {
    render(<SigningDay beat={signingBeat({ signed_count: 2, signings: [{ player_id: 'c1', name: 'Card Kid', ovr: 60, club_name: 'Rival FC', reason: 'r', outcome_kind: 'rival_signing', user_interaction: { scouted: false } }] })} onComplete={() => {}} />);
    // 2 signings claimed by signed_count, even though only 1 (rival) card exists and 0 are my_signing
    expect(screen.getByText(/You signed 2\./)).toBeInTheDocument();
  });

  it('#68: hero tiles label player-scope vs LEAGUE-scope', () => {
    render(<SigningDay beat={signingBeat({ signings: [{ player_id: 'c1', name: 'K', ovr: 60, club_name: 'Rival FC', reason: 'r', outcome_kind: 'rival_signing', user_interaction: { scouted: false } }] })} onComplete={() => {}} />);
    expect(screen.getByText('Your Signings')).toBeInTheDocument();
    expect(screen.getByText(/Rival Signings \(League\)/)).toBeInTheDocument();
    expect(screen.getByText(/Rookies \(League\)/)).toBeInTheDocument();
  });
});

function awardsBeat(awards: unknown[]) {
  return { key: 'awards', beat_index: 1, total_beats: 9, title: 'Awards Night', payload: { awards } } as never;
}

describe('AwardsNight (#75 extra_stats vs season_stat)', () => {
  it('renders extra_stats chips when present', async () => {
    render(<AwardsNight beat={awardsBeat([
      { award_type: 'mvp', award_name: 'MVP', player_name: 'Star', club_name: 'You', ovr: 80, season_stat: 40, career_stat: 120,
        extra_stats: { throw_elims: 33, catches: 12, times_eliminated: 5 } },
    ])} onComplete={() => {}} />);
    await userEvent.click(document.body); // skip the staged reveal to final
    expect(await screen.findByText('THROW ELIMS')).toBeInTheDocument();
    expect(screen.getByText('33')).toBeInTheDocument();
  });

  it('falls back to the single season_stat chip when extra_stats is absent', async () => {
    render(<AwardsNight beat={awardsBeat([
      { award_type: 'mvp', award_name: 'MVP', player_name: 'Star', club_name: 'You', ovr: 80, season_stat: 40, career_stat: 120 },
    ])} onComplete={() => {}} />);
    await userEvent.click(document.body);
    expect(await screen.findByText('SEASON ELIMS')).toBeInTheDocument();
    expect(screen.queryByText('THROW ELIMS')).not.toBeInTheDocument();
  });
});

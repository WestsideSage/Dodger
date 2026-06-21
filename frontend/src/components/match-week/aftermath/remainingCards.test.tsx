/**
 * Vitest guards for the 4 remaining aftermath cards reskinned in Task 7
 * continuation: FalloutGrid, ReplayTimeline, EliminationCeremony,
 * ChampionshipHero. Each test asserts data-* truth hooks survive + core
 * behavior is verbatim (no logic change, presentation only).
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { FalloutGrid } from './FalloutGrid';
import { ReplayTimeline } from './ReplayTimeline';
import { EliminationCeremony } from './EliminationCeremony';
import { ChampionshipHero } from './ChampionshipHero';

// ─── FalloutGrid ────────────────────────────────────────────────────────────

describe('FalloutGrid — data-* truth hooks (Task 7)', () => {
  const baseProps = {
    playerGrowth: [],
    standingsShift: [],
    recruitReactions: [],
  };

  it('keeps data-testid="fallout-grid"', () => {
    render(<FalloutGrid {...baseProps} />);
    expect(screen.getByTestId('fallout-grid')).toBeInTheDocument();
  });

  it('renders growth deltas with player name and delta', () => {
    render(
      <FalloutGrid
        {...baseProps}
        playerGrowth={[
          { player_id: 'p1', player_name: 'Ana Bolt', attribute: 'accuracy', delta: 2 },
        ]}
      />,
    );
    expect(screen.getByText('Ana Bolt')).toBeInTheDocument();
    expect(screen.getByText(/accuracy.*\+2/)).toBeInTheDocument();
  });

  it('shows empty copy when no growth and no dev feedback', () => {
    render(<FalloutGrid {...baseProps} />);
    expect(screen.getByText('No growth logged this week.')).toBeInTheDocument();
  });

  it('shows standings shift with rank arrows', () => {
    render(
      <FalloutGrid
        {...baseProps}
        standingsShift={[{ club_id: 'c1', club_name: 'Vortex', old_rank: 3, new_rank: 1 }]}
      />,
    );
    expect(screen.getByText('Vortex')).toBeInTheDocument();
    expect(screen.getByText(/↑.*#3.*→.*#1/)).toBeInTheDocument();
  });

  it('shows empty copy when no standings shift', () => {
    render(<FalloutGrid {...baseProps} />);
    expect(screen.getByText('Records updated — no rank changes this week.')).toBeInTheDocument();
  });

  it('shows recruit reactions with interest delta', () => {
    render(
      <FalloutGrid
        {...baseProps}
        recruitReactions={[
          { prospect_id: 'r1', prospect_name: 'Kim Stone', interest_delta: '+5', evidence: 'Won big.' },
        ]}
      />,
    );
    expect(screen.getByText('Kim Stone')).toBeInTheDocument();
    expect(screen.getByText('+5')).toBeInTheDocument();
  });

  it('shows empty copy when no recruit reactions', () => {
    render(<FalloutGrid {...baseProps} />);
    expect(screen.getByText('No prospect movement this week.')).toBeInTheDocument();
  });
});

// ─── ReplayTimeline ──────────────────────────────────────────────────────────

describe('ReplayTimeline — data-* truth hooks (Task 7)', () => {
  const baseLane = { title: 'Set 1', summary: 'Opened strong.', items: [] };

  it('returns null when no beats and no moments', () => {
    const { container } = render(
      <ReplayTimeline replay={null} lanes={[]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('keeps data-testid="replay-timeline" when there are beats', () => {
    render(<ReplayTimeline replay={null} lanes={[baseLane]} />);
    expect(screen.getByTestId('replay-timeline')).toBeInTheDocument();
  });

  it('collapse bar is collapsed by default (aria-expanded false)', () => {
    render(<ReplayTimeline replay={null} lanes={[baseLane]} />);
    const bar = screen.getByRole('button');
    expect(bar).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows POSTGAME REPORT label for regular weeks', () => {
    render(<ReplayTimeline replay={null} lanes={[baseLane]} />);
    expect(screen.getByText('POSTGAME REPORT')).toBeInTheDocument();
  });

  it('shows BYE WEEK REPORT label when isBye=true', () => {
    render(<ReplayTimeline replay={null} lanes={[baseLane]} isBye />);
    expect(screen.getByText('BYE WEEK REPORT')).toBeInTheDocument();
  });

  it('shows moment count in meta', () => {
    render(<ReplayTimeline replay={null} lanes={[baseLane, { title: 'Set 2', summary: 'Traded blows.', items: [] }]} />);
    expect(screen.getByText(/2 moments/)).toBeInTheDocument();
  });
});

// ─── EliminationCeremony ─────────────────────────────────────────────────────

const elimBase: NonNullable<import('../../../types').Aftermath['elimination']> = {
  stage: 'Semifinal',
  opponent_name: 'Iron Peak',
  player_score: 2,
  opponent_score: 3,
  decided_by: 'regulation',
  cause: 'Outpaced in set three.',
  contributors: [{ player_name: 'Dan Axe', score: 8.4 }],
  returning: ['Ana Bolt', 'Kai Sun'],
};

describe('EliminationCeremony — data-* truth hooks (Task 7)', () => {
  it('keeps data-testid="elimination-ceremony"', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByTestId('elimination-ceremony')).toBeInTheDocument();
  });

  it('keeps data-testid="elimination-continue" on the button', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByTestId('elimination-continue')).toBeInTheDocument();
  });

  it('renders stage label with Eliminated suffix', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByText('Semifinal · Eliminated')).toBeInTheDocument();
  });

  it('renders player and opponent scores', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText(/vs Iron Peak/)).toBeInTheDocument();
  });

  it('renders cause text', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByText('Outpaced in set three.')).toBeInTheDocument();
  });

  it('renders contributors with formatted score', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByText('Dan Axe')).toBeInTheDocument();
    expect(screen.getByText('8.4')).toBeInTheDocument();
  });

  it('renders returning players list', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} />);
    expect(screen.getByText('Ana Bolt · Kai Sun')).toBeInTheDocument();
  });

  it('shows Advancing text when isAdvancing=true and button is disabled', () => {
    render(<EliminationCeremony elimination={elimBase} onContinue={() => {}} isAdvancing />);
    const btn = screen.getByTestId('elimination-continue');
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent('Advancing…');
  });
});

// ─── ChampionshipHero ─────────────────────────────────────────────────────────

const champBase: NonNullable<import('../../../types').Aftermath['championship']> = {
  champion_name: 'Aurora FC',
  opponent_name: 'Iron Peak',
  player_score: 3,
  opponent_score: 1,
  decided_by: 'regulation',
};

describe('ChampionshipHero — data-* truth hooks (Task 7)', () => {
  it('keeps data-testid="championship-hero"', () => {
    render(<ChampionshipHero championship={champBase} />);
    expect(screen.getByTestId('championship-hero')).toBeInTheDocument();
  });

  it('renders the Champions kicker', () => {
    render(<ChampionshipHero championship={champBase} />);
    expect(screen.getByText('Champions')).toBeInTheDocument();
  });

  it('renders champion_name as heading', () => {
    render(<ChampionshipHero championship={champBase} />);
    expect(screen.getByRole('heading', { name: 'Aurora FC' })).toBeInTheDocument();
  });

  it('renders score and opponent in subtitle', () => {
    render(<ChampionshipHero championship={champBase} />);
    expect(screen.getByText(/3–1 over Iron Peak/)).toBeInTheDocument();
  });

  it('appends "in overtime" when decided_by=overtime', () => {
    render(
      <ChampionshipHero
        championship={{ ...champBase, decided_by: 'overtime' }}
      />,
    );
    expect(screen.getByText(/in overtime to take the title/)).toBeInTheDocument();
  });

  it('appends "on the tiebreaker" when decided_by=seed_tiebreaker', () => {
    render(
      <ChampionshipHero
        championship={{ ...champBase, decided_by: 'seed_tiebreaker' }}
      />,
    );
    expect(screen.getByText(/on the tiebreaker to take the title/)).toBeInTheDocument();
  });

  it('no suffix when decided_by=regulation', () => {
    render(<ChampionshipHero championship={champBase} />);
    // Should NOT contain "overtime" or "tiebreaker"
    expect(screen.queryByText(/overtime|tiebreaker/)).not.toBeInTheDocument();
  });
});

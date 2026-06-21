// frontend/src/components/dynasty/history/ProgramModal.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, expectTypeOf, vi } from 'vitest';
import type { ComponentProps } from 'react';
import { ProgramModal } from './ProgramModal';

// MyProgramView fetches; stub it so this test exercises ONLY the modal frame.
vi.mock('./MyProgramView', () => ({
  MyProgramView: ({ isSelf }: { clubId: string; isSelf?: boolean }) => (
    <div data-testid="stub-myprogram" data-is-self={String(isSelf)} />
  ),
}));

describe('ProgramModal (P5-owned, P4-consumed — frozen contract)', () => {
  it('accepts exactly { clubId, clubName, onClose }', () => {
    expectTypeOf<ComponentProps<typeof ProgramModal>>()
      .toEqualTypeOf<{ clubId: string; clubName: string; onClose: () => void }>();
  });

  it('renders a labelled dialog with the club name and forces isSelf=false (#97)', () => {
    render(<ProgramModal clubId="hammers" clubName="Granite City Hammers" onClose={() => {}} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Granite City Hammers')).toBeInTheDocument();
    expect(screen.getByTestId('stub-myprogram')).toHaveAttribute('data-is-self', 'false');
  });

  it('exposes the overlay via a stable testid (the command-policy-overlay global was migrated to a CSS Module)', () => {
    render(
      <ProgramModal clubId="hammers" clubName="Granite City Hammers" onClose={() => {}} />,
    );
    // The shared overlay chrome moved from the global `command-policy-overlay`
    // class into components/chrome.module.css; the stable hook is now the testid.
    expect(screen.getByTestId('program-archive-modal')).toBeInTheDocument();
  });
});

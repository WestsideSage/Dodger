// frontend/src/components/dynasty/HistorySubTab.test.tsx
// NOTE: placed in dynasty/ (same dir as HistorySubTab.tsx), NOT in dynasty/history/.
// vi.mock specifiers match the EXACT strings HistorySubTab.tsx uses (lines 2-3):
//   import { MyProgramView } from './history/MyProgramView';
//   import { LeagueView } from './history/LeagueView';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { HistorySubTab } from './HistorySubTab';

vi.mock('./history/MyProgramView', () => ({ MyProgramView: () => <div data-testid="stub-mp" /> }));
vi.mock('./history/LeagueView', () => ({ LeagueView: () => <div data-testid="stub-lv" /> }));

describe('HistorySubTab (#97 self-only label)', () => {
  it('labels the program tab "My Program" when isSelf and "Program" otherwise', () => {
    const { rerender } = render(<HistorySubTab clubId="hammers" isSelf />);
    expect(screen.getByRole('button', { name: 'My Program' })).toBeInTheDocument();
    rerender(<HistorySubTab clubId="rivals" isSelf={false} />);
    expect(screen.getByRole('button', { name: 'Program' })).toBeInTheDocument();
  });
});

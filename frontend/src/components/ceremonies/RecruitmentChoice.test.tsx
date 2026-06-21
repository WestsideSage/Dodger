import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../legibility/KnownValue', () => ({ KnownValue: ({ value }: { value?: unknown }) => <span>{value as never}</span> }));
vi.mock('../../legibility/CeilingGrade', () => ({ CeilingGrade: () => null }));

import { RecruitmentChoice } from './RecruitmentChoice';

function recruitBeat(payload: Record<string, unknown>) {
  return {
    key: 'recruitment', beat_index: 8, total_beats: 9,
    payload: {
      available_prospects: [{ prospect_id: 'pr1', name: 'Hot Prospect', kind: 'prospect', archetype: 'Gunner', hometown: 'Town', age: 18, public_ovr_band: [60, 66], scouted: false }],
      signed_count: 0, signing_limit: 3, remaining_signings: 3,
      roster_size: 12, roster_limit: 12, user_roster: [{ id: 'u1', name: 'Old Vet', overall: 58, age: 31 }],
      can_skip: true, skip_blocked_reason: null, other_signings: [], ...payload,
    },
  } as never;
}

describe('RecruitmentChoice (#73 sign-over-cut / #74 skip gate)', () => {
  it('#73: a full roster opens the release picker instead of signing immediately', async () => {
    const onSign = vi.fn();
    render(<RecruitmentChoice beat={recruitBeat({})} onSign={onSign} acting={false} />);
    await userEvent.click(screen.getByRole('button', { name: /^Sign/i }));
    expect(screen.getByTestId('signing-release-picker')).toBeInTheDocument();
    expect(onSign).not.toHaveBeenCalled(); // not fired until a release is named
  });

  it('#74: skip is disabled with a visible reason when the backend blocks it', () => {
    render(<RecruitmentChoice beat={recruitBeat({ can_skip: false, skip_blocked_reason: 'Roster below the floor.' })} onSign={() => {}} acting={false} />);
    expect(screen.getByText(/Roster below the floor/i)).toBeInTheDocument();
  });
});

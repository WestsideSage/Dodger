// frontend/src/components/dynasty/history/ProgramModal.contract.test.tsx
import { describe, it, expectTypeOf } from 'vitest';
import { ProgramModal } from './ProgramModal';
import type { ComponentProps } from 'react';

describe('ProgramModal public contract (frozen for P4 consumers)', () => {
  it('accepts exactly { clubId, clubName, onClose }', () => {
    expectTypeOf<ComponentProps<typeof ProgramModal>>()
      .toEqualTypeOf<{ clubId: string; clubName: string; onClose: () => void }>();
  });
});

import { describe, it, expect, vi, afterEach } from 'vitest';
import { saveApi } from './client';

afterEach(() => vi.restoreAllMocks());

describe('saveApi wizard endpoints', () => {
  it('startingStaff calls the seeded endpoint via the client', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ departments: [] }), { status: 200 }),
    );
    await saveApi.startingStaff(123);
    expect(spy).toHaveBeenCalledWith('/api/saves/starting-staff?seed=123', undefined);
  });
  it('startingProspects calls the seeded endpoint via the client', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ prospects: [] }), { status: 200 }),
    );
    await saveApi.startingProspects(123);
    expect(spy).toHaveBeenCalledWith('/api/saves/starting-prospects?seed=123', undefined);
  });
});

import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('diagnostic playable loop: save, status, simulate, replay, next state', async ({ request }) => {
  const evidence: Record<string, unknown> = {};
  const saveName = `e2e-diagnostics-${Date.now()}`;

  await test.step('create and activate a managed save', async () => {
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora', root_seed: 20260426 },
    });
    evidence.createStatus = create.status();
    expect(create.ok(), JSON.stringify(evidence)).toBeTruthy();

    const saveState = await request.get(`${baseUrl}/api/save-state`);
    const payload = await saveState.json();
    evidence.activePath = payload.active_path;
    expect(payload.loaded, JSON.stringify(evidence)).toBe(true);
  });

  await test.step('confirm command center is playable before sim', async () => {
    const command = await request.get(`${baseUrl}/api/command-center`);
    evidence.commandStatus = command.status();
    expect(command.ok(), JSON.stringify(evidence)).toBeTruthy();
    const payload = await command.json();
    evidence.week = payload.week;
    evidence.intent = payload.plan?.intent;
    expect(payload.plan?.lineup?.player_ids?.length, JSON.stringify(evidence)).toBeGreaterThanOrEqual(6);
  });

  let matchId = '';
  await test.step('simulate one command week and capture replay id', async () => {
    const simulated = await request.post(`${baseUrl}/api/command-center/simulate`, {
      data: { intent: 'Win Now' },
    });
    evidence.simulateStatus = simulated.status();
    expect(simulated.ok(), JSON.stringify(evidence)).toBeTruthy();
    const payload = await simulated.json();
    matchId = payload.dashboard?.match_id ?? '';
    evidence.matchId = matchId;
    evidence.nextState = payload.next_state;
    expect(matchId, JSON.stringify(evidence)).toBeTruthy();
    expect(payload.dashboard?.lanes?.length, JSON.stringify(evidence)).toBeGreaterThan(0);
  });

  await test.step('verify replay proof is inspectable from saved event truth', async () => {
    const replay = await request.get(`${baseUrl}/api/matches/${encodeURIComponent(matchId)}/replay`);
    evidence.replayStatus = replay.status();
    expect(replay.ok(), JSON.stringify(evidence)).toBeTruthy();
    const payload = await replay.json();
    evidence.eventCount = payload.events?.length;
    evidence.proofCount = payload.proof_events?.length;
    evidence.keyPlayCount = payload.key_play_indices?.length;
    expect(payload.events?.length, JSON.stringify(evidence)).toBeGreaterThan(0);
    expect(payload.proof_events?.length, JSON.stringify(evidence)).toBeGreaterThan(0);
    expect(payload.report?.evidence_lanes?.length, JSON.stringify(evidence)).toBeGreaterThan(0);
  });
});

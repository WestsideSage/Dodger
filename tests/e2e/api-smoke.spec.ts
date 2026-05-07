import { test, expect } from '@playwright/test';

test('backend save state endpoint is reachable before a save is loaded', async ({ request }) => {
  const response = await request.get('http://127.0.0.1:8000/api/save-state');
  expect(response.ok()).toBeTruthy();

  const saveState = await response.json();
  expect(saveState).toHaveProperty('loaded');
  expect(saveState).toHaveProperty('active_path');
});

import { expect, type APIRequestContext } from '@playwright/test';

/**
 * WT-12 launch-token injection for raw APIRequestContext calls.
 *
 * The live server enforces a per-process launch token on EVERY mutating
 * (POST/PUT/PATCH/DELETE) `/api/` request (server.py `_launch_token_guard`),
 * with no exemption for any route — `/api/saves/new` and `/api/saves/unload`
 * included. Browser page-driven requests carry the token automatically: the
 * served index.html embeds it as `<meta name="launch-token">` and the SPA
 * client (frontend/src/api/client.ts) attaches it as the
 * `X-Dodgeball-Launch-Token` header (falling back to GET /api/launch-token
 * when the meta tag is absent).
 *
 * Raw `request.post(...)` calls from a spec bypass the SPA entirely, so they
 * must fetch and attach the real token themselves. This helper does exactly
 * that against the REAL guard — it does not, and must not, disable the guard.
 *
 * The token is read from the unguarded GET /api/launch-token endpoint, which
 * returns `{ "token": <value> }`. We assert that shape loudly so a future
 * endpoint/payload rename surfaces here as a failure rather than silently
 * regressing the specs to unauthenticated-but-passing-for-the-wrong-reason.
 */
export async function launchTokenHeaders(
  request: APIRequestContext,
  baseUrl = 'http://127.0.0.1:8000',
): Promise<Record<string, string>> {
  const response = await request.get(`${baseUrl}/api/launch-token`);
  expect(
    response.ok(),
    'GET /api/launch-token must succeed (it is a non-mutating, guard-exempt endpoint)',
  ).toBeTruthy();
  const payload = (await response.json()) as { token?: unknown };
  expect(
    typeof payload.token === 'string' && (payload.token as string).length > 0,
    'GET /api/launch-token must return a non-empty { token } string',
  ).toBeTruthy();
  return { 'X-Dodgeball-Launch-Token': payload.token as string };
}

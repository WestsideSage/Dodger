import fs from 'node:fs/promises';
import path from 'node:path';

const DEFAULT_TABS = ['command', 'hub', 'roster', 'tactics', 'standings', 'schedule', 'news'];

function timestamp() {
  return new Date().toISOString();
}

function sanitizeName(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function truncate(value, limit = 1200) {
  if (!value) return '';
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function writeJson(filePath, value) {
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

async function saveScreenshot(tab, outputDir, name, results, options = {}) {
  const image = await tab.playwright.screenshot({ fullPage: options.fullPage ?? false });
  const base64 = await image.toBase64();
  const filePath = path.join(outputDir, 'screenshots', `${sanitizeName(name)}.png`);
  await fs.writeFile(filePath, Buffer.from(base64, 'base64'));
  results.screenshots.push({ name, file: filePath, at: timestamp() });
  return { image, filePath };
}

async function recordConsole(tab, outputDir, name, results) {
  let logs = [];
  try {
    logs = await tab.dev.logs({ levels: ['error', 'warning', 'warn'], limit: 100 });
  } catch (error) {
    results.notes.push(`Could not collect console logs at ${name}: ${error.message}`);
  }
  const filePath = path.join(outputDir, 'console', `${sanitizeName(name)}.json`);
  await writeJson(filePath, logs);
  results.console.push({ name, file: filePath, count: logs.length, at: timestamp() });
  if (logs.length) {
    results.findings.push({
      id: `console-${results.findings.length + 1}`,
      severity: 'medium',
      title: `Console warnings/errors after ${name}`,
      evidence: filePath,
      detail: logs.map(log => log.message).slice(0, 5),
    });
  }
  return logs;
}

async function apiRequest(baseUrl, route, options = {}) {
  const response = await fetch(`${baseUrl}${route}`, options);
  const text = await response.text();
  let body = text;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return {
    route,
    status: response.status,
    ok: response.ok,
    body,
  };
}

async function snapshotApi(baseUrl, outputDir, name, routes, results) {
  const records = [];
  for (const route of routes) {
    try {
      records.push(await apiRequest(baseUrl, route));
    } catch (error) {
      records.push({ route, ok: false, error: error.message });
    }
  }
  const filePath = path.join(outputDir, 'api', `${sanitizeName(name)}.json`);
  await writeJson(filePath, records);
  results.apiSnapshots.push({ name, file: filePath, at: timestamp() });
  return records;
}

async function waitForText(tab, text, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  let lastSnapshot = '';
  while (Date.now() < deadline) {
    lastSnapshot = await tab.playwright.domSnapshot();
    if (lastSnapshot.includes(text)) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for text "${text}". Last snapshot: ${truncate(lastSnapshot)}`);
}

async function waitForAnyText(tab, texts, timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  let lastSnapshot = '';
  while (Date.now() < deadline) {
    lastSnapshot = await tab.playwright.domSnapshot();
    const matched = texts.find(text => lastSnapshot.includes(text));
    if (matched) return matched;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for any of ${texts.join(', ')}. Last snapshot: ${truncate(lastSnapshot)}`);
}

async function clickButton(tab, name, results, options = {}) {
  const locator = options.testId
    ? (options.scope || tab.playwright).getByTestId(options.testId)
    : (options.scope || tab.playwright).getByRole('button', { name, exact: options.exact ?? true });

  try {
    await locator.first().waitFor({ state: 'visible', timeout: 10000 });
  } catch (e) {
    // Ignore timeout; count check handles it
  }

  const count = await locator.count();
  if (count !== 1) {
    throw new Error(`Expected one button named "${name}", found ${count}`);
  }
  const enabled = await locator.isEnabled();
  results.actions.push({ action: 'button-state', name, enabled, at: timestamp() });
  if (!enabled && !options.allowDisabled) {
    throw new Error(`Button "${name}" is disabled`);
  }
  if (enabled) {
    await locator.click({ timeout: 8000 });
    results.actions.push({ action: 'click', name, at: timestamp() });
  }
  return enabled;
}

function tabLabel(tabName) {
  const labels = {
    command: 'Command Center',
    hub: 'Hub',
    roster: 'Roster',
    tactics: 'Tactics',
    standings: 'Standings',
    schedule: 'Schedule',
    news: 'News',
  };
  return labels[tabName] ?? tabName;
}

async function clickTab(tab, name, results) {
  const locator = tab.playwright.getByRole('button', { name: new RegExp('^' + tabLabel(name)), exact: false });
  const count = await locator.count();
  if (count !== 1) throw new Error(`Expected one tab button "${name}", found ${count}`);
  await locator.click({ timeoutMs: 8000 });
  await waitForText(tab, screenHeading(name), 8000);
  results.actions.push({ action: 'tab', name, url: await tab.url(), at: timestamp() });
}

async function clickNavOnly(tab, name, results) {
  const locator = tab.playwright.getByRole('button', { name: new RegExp('^' + tabLabel(name)), exact: false });
  const count = await locator.count();
  if (count !== 1) throw new Error(`Expected one nav button "${name}", found ${count}`);
  await locator.click({ timeoutMs: 8000 });
  results.actions.push({ action: 'nav-only', name, url: await tab.url(), at: timestamp() });
}

function screenHeading(tabName) {
  const headings = {
    command: 'Command Center',
    hub: 'Season Hub',
    roster: 'Team Roster',
    tactics: 'Coach Policy',
    standings: 'Standings',
    schedule: 'Schedule',
    news: 'News',
  };
  return headings[tabName] ?? tabName;
}

async function assertText(tab, text, label, results) {
  const count = await tab.playwright.getByText(text, { exact: false }).count();
  const passed = count > 0;
  results.assertions.push({ label, passed, text, count, at: timestamp() });
  if (!passed) {
    results.findings.push({
      id: `missing-${results.findings.length + 1}`,
      severity: 'high',
      title: `Missing expected text: ${label}`,
      detail: `Could not find "${text}" on ${await tab.url()}`,
    });
  }
  return passed;
}

async function crawlScreens(tab, baseUrl, outputDir, results) {
  for (const tabName of DEFAULT_TABS) {
    await clickTab(tab, tabName, results);
    await assertText(tab, screenHeading(tabName), `${tabName} heading`, results);
    const shot = await saveScreenshot(tab, outputDir, `screen-${tabName}`, results, { fullPage: true });
    if (tabName === 'hub' || tabName === 'tactics') {
      await results.display(shot.image);
    }
    await recordConsole(tab, outputDir, `screen-${tabName}`, results);
    await snapshotApi(baseUrl, outputDir, `screen-${tabName}`, ['/api/status'], results);
  }
}

async function exerciseTactics(tab, baseUrl, outputDir, results) {
  await clickTab(tab, 'tactics', results);
  const sliders = tab.playwright.locator('input[type="range"]');
  const sliderCount = await sliders.count();
  results.assertions.push({
    label: 'Eight tactics sliders are present',
    passed: sliderCount === 8,
    expected: 8,
    actual: sliderCount,
    at: timestamp(),
  });
  if (sliderCount !== 8) {
    results.findings.push({
      id: `tactics-${results.findings.length + 1}`,
      severity: 'high',
      title: 'Tactics screen does not expose all eight CoachPolicy controls',
      detail: `Expected 8 range inputs, found ${sliderCount}`,
    });
    return;
  }

  const setAllSliders = async (mode) => {
    const allSliders = await sliders.all();
    for (const slider of allSliders) {
      await slider.click({ timeoutMs: 5000 });
      if (mode === '0') {
        await slider.press('Home', { timeoutMs: 5000 });
      } else if (mode === '1') {
        await slider.press('End', { timeoutMs: 5000 });
      } else {
        await slider.press('Home', { timeoutMs: 5000 });
        for (let step = 0; step < 50; step += 1) {
          await slider.press('ArrowRight', { timeoutMs: 5000 });
        }
      }
    }
  };

  const values = ['0', '1', '0.5'];
  for (const value of values) {
    await setAllSliders(value);
    const saveCount = await tab.playwright.getByRole('button', { name: 'Save Tactics', exact: true }).count();
    if (saveCount !== 1) {
      results.findings.push({
        id: `tactics-save-${results.findings.length + 1}`,
        severity: 'high',
        title: 'Tactics slider changes did not expose Save Tactics',
        detail: `After setting all sliders to ${value}, expected one Save Tactics button and found ${saveCount}.`,
      });
      await saveScreenshot(tab, outputDir, `tactics-save-missing-${value.replace('.', '-')}`, results, { fullPage: true });
      continue;
    }
    await clickButton(tab, 'Save Tactics', results, { exact: true });
    await waitForText(tab, 'Tactics saved.', 8000);
    await saveScreenshot(tab, outputDir, `tactics-saved-${value.replace('.', '-')}`, results, { fullPage: true });
    await snapshotApi(baseUrl, outputDir, `tactics-api-${value.replace('.', '-')}`, ['/api/tactics'], results);
  }

  await tab.reload();
  await waitForText(tab, 'Coach Policy', 8000);
  await assertText(tab, 'Saved', 'tactics reload keeps saved state button', results);
  await recordConsole(tab, outputDir, 'tactics-after-reload', results);
}

async function exerciseReplay(tab, baseUrl, outputDir, results) {
  await clickTab(tab, 'hub', results);

  // Wait for the hub state to stabilize
  const state = await waitForAnyText(tab, ['Match Report', 'Season Hub', 'Loading hub'], 15000);
  
  // Check if a replay is already pending (common in V5 after Command Center simulation)
  const isReplayPending = (await tab.playwright.getByText('Match Report', { exact: false }).count()) > 0;

  if (!isReplayPending) {
    const canPlay = await clickButton(tab, 'Play Next Match', results, { allowDisabled: true, exact: false });
    if (!canPlay) {
      results.findings.push({
        id: `replay-${results.findings.length + 1}`,
        severity: 'medium',
        title: 'Play Next Match was disabled at start of replay flow',
        detail: 'The current career state did not allow the replay path from the hub and no replay was pending.',
      });
      return false;
    }
    await saveScreenshot(tab, outputDir, 'replay-clicking-match', results, { fullPage: true });
    const postPlayState = await waitForAnyText(tab, ['Match Report', 'Simulation complete', 'Error:'], 30000);
    if (postPlayState !== 'Match Report') {
      const snapshot = await tab.playwright.domSnapshot();
      results.findings.push({
        id: `replay-${results.findings.length + 1}`,
        severity: 'high',
        title: 'Play Next Match did not open match replay',
        detail: `After clicking Play Next Match, the hub showed "${postPlayState}" instead of Match Replay. Snapshot excerpt: ${truncate(snapshot)}`,
      });
      await saveScreenshot(tab, outputDir, 'replay-not-opened', results, { fullPage: true });
      return false;
    }
  }
  await assertText(tab, 'Match Report', 'replay report is visible', results);
  await assertText(tab, 'Top Performers', 'top performers visible', results);
  let shot = await saveScreenshot(tab, outputDir, 'replay-start', results, { fullPage: true });
  await results.display(shot.image);
  await snapshotApi(baseUrl, outputDir, 'replay-pending', ['/api/status', '/api/news', '/api/schedule'], results);

  await clickButton(tab, 'Next', results, { allowDisabled: true });
  await clickButton(tab, 'Key Play', results, { allowDisabled: true });
  await clickButton(tab, 'Back', results, { allowDisabled: true });
  await saveScreenshot(tab, outputDir, 'replay-navigation', results, { fullPage: true });

  await tab.reload();
  await waitForText(tab, 'Match Report', 12000);
  await assertText(tab, 'Match Report', 'pending replay survives reload', results);
  await saveScreenshot(tab, outputDir, 'replay-after-reload', results, { fullPage: true });

  await clickTab(tab, 'roster', results);
  await clickNavOnly(tab, 'hub', results);
  await waitForText(tab, 'Match Report', 12000);
  await assertText(tab, 'Match Report', 'pending replay survives tab switch', results);

  await clickButton(tab, 'Continue', results, { exact: false });
  await waitForText(tab, 'Season Hub', 12000);
  await assertText(tab, 'Play Next Match', 'hub returns after replay continue', results);
  await snapshotApi(baseUrl, outputDir, 'after-replay-continue', ['/api/status', '/api/news', '/api/schedule'], results);
  await recordConsole(tab, outputDir, 'after-replay-continue', results);
  return true;
}

async function exerciseProgression(tab, baseUrl, outputDir, results) {
  await clickTab(tab, 'hub', results);
  const buttons = ['Sim Week', 'Sim To User Match', 'Sim 2 Weeks', 'Sim To Playoffs'];
  for (const name of buttons) {
    await clickTab(tab, 'hub', results);
    const wasEnabled = await clickButton(tab, name, results, { allowDisabled: true, exact: false });
    if (!wasEnabled) {
      results.notes.push(`${name} was disabled during progression flow.`);
      continue;
    }
    const replayVisible = await tab.playwright.getByText('Match Report', { exact: false }).count();
    if (replayVisible > 0) {
      await saveScreenshot(tab, outputDir, `progression-${name}-replay`, results, { fullPage: true });
      await clickButton(tab, 'Continue', results, { exact: false });
      await waitForText(tab, 'Season Hub', 12000);
    } else {
      await waitForText(tab, 'Simulation complete', 20000);
      await assertText(tab, 'Simulation complete', `${name} reports completion`, results);
      await saveScreenshot(tab, outputDir, `progression-${name}`, results, { fullPage: true });
    }
    await snapshotApi(baseUrl, outputDir, `progression-${name}`, ['/api/status', '/api/standings', '/api/schedule', '/api/news'], results);
    await recordConsole(tab, outputDir, `progression-${name}`, results);
  }
}

async function exerciseBrowserAbuse(tab, baseUrl, outputDir, results) {
  await clickTab(tab, 'hub', results);
  const spamTargets = ['Play Next Match', 'Sim Week'];
  for (const name of spamTargets) {
    const locator = tab.playwright.getByRole('button', { name, exact: true });
    const count = await locator.count();
    if (count !== 1 || !(await locator.isEnabled())) {
      results.notes.push(`Skipped spam target ${name}; count=${count}.`);
      continue;
    }
    await locator.click({ timeoutMs: 5000 });
    try {
      await locator.click({ timeoutMs: 1000 });
    } catch (error) {
      results.actions.push({ action: 'expected-spam-click-failure', name, detail: error.message, at: timestamp() });
    }
    const replayVisible = await tab.playwright.getByText('Match Report', { exact: false }).count();
    if (replayVisible > 0) {
      await saveScreenshot(tab, outputDir, `spam-${name}-replay`, results, { fullPage: true });
      await clickButton(tab, 'Continue', results, { exact: false });
      await waitForText(tab, 'Season Hub', 12000);
    } else {
      await waitForText(tab, 'Season Hub', 12000);
    }
  }

  await tab.goto(`${baseUrl}/api/not-real`);
  await tab.playwright.waitForLoadState('domcontentloaded', { timeout: 8000 });
  const api404 = await tab.playwright.domSnapshot();
  results.assertions.push({
    label: 'Unknown API route is not SPA shell',
    passed: api404.includes('not_found') || api404.includes('404') || api404.includes('Unknown API route'),
    excerpt: truncate(api404),
    at: timestamp(),
  });
  await saveScreenshot(tab, outputDir, 'unknown-api-route', results, { fullPage: true });

  await tab.goto(`${baseUrl}/deep/bad/path`);
  await tab.playwright.waitForLoadState('domcontentloaded', { timeout: 8000 });
  await assertText(tab, 'Dodgeball Manager', 'SPA fallback loads for non-api path', results);
  await saveScreenshot(tab, outputDir, 'bad-spa-path', results, { fullPage: true });

  await tab.back();
  await tab.forward();
  await recordConsole(tab, outputDir, 'browser-back-forward', results);

  results.notes.push('Mobile-width visual inspection was not automated because the in-app browser API exposed in this session does not include viewport resizing.');
}

async function exerciseCommandCenter(tab, baseUrl, outputDir, results) {
  await clickTab(tab, 'command', results);
  const canSim = await clickButton(tab, 'Simulate Command Week', results, { testId: 'simulate-command-week', allowDisabled: true });
  if (!canSim) {
    results.notes.push('Simulate Command Week was disabled.');
    return false;
  }
  
  await waitForText(tab, 'Post-Week Dashboard', 30000);
  await assertText(tab, 'Post-Week Dashboard', 'Command center dashboard generated', results);
  await saveScreenshot(tab, outputDir, 'command-dashboard', results, { fullPage: true });
  await snapshotApi(baseUrl, outputDir, 'command-sim', ['/api/command-center', '/api/status', '/api/news'], results);
  return true;
}

export async function runAdversarialBrowserPlaythrough({
  tab,
  display,
  baseUrl = 'http://127.0.0.1:8000',
  outputDir,
} = {}) {
  if (!tab) throw new Error('runAdversarialBrowserPlaythrough requires a browser tab.');
  if (!outputDir) throw new Error('runAdversarialBrowserPlaythrough requires outputDir.');

  const results = {
    startedAt: timestamp(),
    baseUrl,
    outputDir,
    actions: [],
    assertions: [],
    screenshots: [],
    console: [],
    apiSnapshots: [],
    findings: [],
    notes: [],
    display: display ?? (async () => {}),
  };

  await ensureDir(outputDir);
  await ensureDir(path.join(outputDir, 'screenshots'));
  await ensureDir(path.join(outputDir, 'console'));
  await ensureDir(path.join(outputDir, 'api'));

  try {
    await snapshotApi(baseUrl, outputDir, 'preflight', ['/api/status', '/api/roster', '/api/tactics'], results);
    await tab.goto(baseUrl);
    await tab.playwright.waitForLoadState('domcontentloaded', { timeout: 12000 });
    await waitForText(tab, 'Dodgeball Manager', 12000);
    await saveScreenshot(tab, outputDir, 'initial-load', results, { fullPage: true });
    await crawlScreens(tab, baseUrl, outputDir, results);
    await exerciseReplay(tab, baseUrl, outputDir, results);
    await exerciseCommandCenter(tab, baseUrl, outputDir, results);
    await exerciseTactics(tab, baseUrl, outputDir, results);
    await exerciseProgression(tab, baseUrl, outputDir, results);
    await exerciseBrowserAbuse(tab, baseUrl, outputDir, results);
  } catch (error) {
    results.findings.push({
      id: `fatal-${results.findings.length + 1}`,
      severity: 'critical',
      title: 'Browser playthrough stopped early',
      detail: error.stack || error.message,
    });
    try {
      await saveScreenshot(tab, outputDir, 'fatal-state', results, { fullPage: true });
    } catch (screenshotError) {
      results.notes.push(`Could not capture fatal screenshot: ${screenshotError.message}`);
    }
  } finally {
    delete results.display;
    results.finishedAt = timestamp();
    results.passedAssertions = results.assertions.filter(item => item.passed).length;
    results.failedAssertions = results.assertions.filter(item => item.passed === false).length;
    results.findingCount = results.findings.length;
    await writeJson(path.join(outputDir, 'results.json'), results);
  }

  return results;
}

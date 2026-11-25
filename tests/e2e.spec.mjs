import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:8766';   // the isolated test stack
const NAME = process.env.E2E_NAME;
const ZIP = process.env.E2E_ZIP;
const NAME_1M = process.env.E2E_NAME_1M;
const ZIP_1M = process.env.E2E_ZIP_1M;
const OUT = '/work/tests/out';
const REF = '/work/tests/sets/rate-limiter-py/reference';
const H = { 'X-ILab': '1' };

// The set picker is a custom dropdown: open it, then click the option for this set name.
async function pickSet(page, name) {
  await page.click('#set-picker');
  await page.click(`#set-picker-list [data-value="${name}"]`);
}

function walk(d, base = d) {
  return fs.readdirSync(d, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? walk(path.join(d, e.name), base) : [path.relative(base, path.join(d, e.name))]);
}

test('full interview flow', async ({ page, request }) => {
  const shot = n => page.screenshot({ path: `${OUT}/e2e-${n}.png` });
  const api = async p => (await request.get(BASE + p, { headers: H })).json();

  await page.goto(BASE);
  await shot('0-home');

  // real drop event
  const bytes = Array.from(fs.readFileSync(ZIP));
  const dt = await page.evaluateHandle(b => {
    const d = new DataTransfer();
    d.items.add(new File([new Uint8Array(b)], 'set.zip', { type: 'application/zip' }));
    return d;
  }, bytes);
  const dz = page.locator('#dropzone');
  const target = (await dz.count()) && (await dz.isVisible()) ? '#dropzone' : 'body';
  for (const t of ['dragenter', 'dragover', 'drop']) await page.dispatchEvent(target, t, { dataTransfer: dt });

  // wait for the import to land, then make sure the ready screen shows this set
  await expect.poll(async () => (await api('/api/sets')).sets.some(s => s.name === NAME), { timeout: 30000 }).toBe(true);
  const info = await api(`/api/sets/${NAME}`);
  try { await expect(page.locator('#ready')).toContainText(info.title, { timeout: 8000 }); }
  catch { await pickSet(page, NAME).catch(() => page.getByText(info.title).first().click());
          await expect(page.locator('#ready')).toContainText(info.title); }
  await shot('1-ready');
  await expect(page.locator('#ready-name')).toHaveText(NAME);
  await page.click('#set-picker');
  await expect(page.locator(`#set-picker-list [data-value="${NAME}"]`)).toContainText(`${NAME} · not started`);
  await page.keyboard.press('Escape');

  // nothing leaks before Start
  const pb = await page.locator('#problem').count() ? await page.locator('#problem').first().textContent() : '';
  expect((pb || '').trim()).toBe('');
  expect((await request.get(`${BASE}/api/sets/${NAME}/state`, { headers: H })).status()).toBe(409);
  expect(JSON.stringify(info)).not.toContain('"problem"');

  // Start
  await page.click('#start-btn');
  await expect(page.locator('#round')).toBeVisible();
  await page.click('#set-picker');
  await expect(page.locator(`#set-picker-list [data-value="${NAME}"]`)).toContainText('min left');
  await page.keyboard.press('Escape');
  const t1 = await page.locator('#timer').textContent();
  await page.waitForTimeout(2500);
  const t2 = await page.locator('#timer').textContent();
  expect(t2).not.toBe(t1);
  await expect(page.locator('#problem')).not.toHaveText('');
  const p1len = (await page.locator('#problem').textContent()).length;
  await shot('2-round');

  // Run (button, then Ctrl+')
  const st = await api(`/api/sets/${NAME}/state`);
  await page.click('#run-btn');
  await expect(page.locator('#verdict')).toBeVisible({ timeout: 120000 });
  if (st.run_entry && st.testcases_count > 0) await expect(page.locator('body')).toContainText(/[✓✗]/);
  await shot('3-run');
  const [rq] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/run'), { timeout: 10000 }),
    page.keyboard.press("Control+'"),
  ]);
  expect(rq.method()).toBe('POST');
  await expect(page.locator('#verdict')).toBeVisible({ timeout: 120000 });

  // Submit with starter
  await page.click('#submit-btn');
  await expect(page.locator('#results')).toContainText('0/', { timeout: 180000 });
  await shot('4-submit-starter');

  // reference solution via API, reload, submit again
  await page.waitForTimeout(2000);
  for (const f of walk(REF)) {
    const r = await request.put(`${BASE}/api/sets/${NAME}/files/${f}`, { headers: H, data: fs.readFileSync(path.join(REF, f), 'utf8') });
    expect(r.ok()).toBeTruthy();
  }
  await page.reload();
  await expect(page.locator('#round')).toBeVisible({ timeout: 15000 });
  await page.keyboard.press('Control+Enter').catch(() => {});
  const revealed = async () => (await api(`/api/sets/${NAME}/state`)).parts.length > 0;
  if (!(await expect.poll(revealed, { timeout: 90000 }).toBe(true).then(() => true, () => false))) await page.click('#submit-btn');
  await expect.poll(revealed, { timeout: 120000 }).toBe(true);
  const st2 = await api(`/api/sets/${NAME}/state`);
  const snippet = st2.parts[0].md.split('\n').map(l => l.replace(/[#*`_>]/g, '').trim()).find(Boolean).split(/\s+/).slice(0, 3).join(' ');
  await expect(page.locator('#problem')).toContainText(snippet, { timeout: 15000 });
  expect((await page.locator('#problem').textContent()).length).toBeGreaterThan(p1len);
  await shot('5-p2-revealed');

  // End
  await page.click('#end-btn');
  await page.click('#end-confirm');
  await expect(page.locator('#final')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#final')).toContainText(/\d+\s*\/\s*\d+/);
  await shot('6-final');
  await expect(page.locator('#final .late')).toHaveCount(0);  // an on-time End has no "after time" rows

  // Export
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click((await page.locator('#final-export').isVisible()) ? '#final-export' : '#export-btn')]);
  const zp = `${OUT}/e2e-export.zip`;
  await dl.saveAs(zp);
  await expect(page.locator('#flash')).toBeVisible();
  await expect(page.locator('#flash')).toContainText('export.zip');
  // Close the card: the closed bar stays
  await page.click('#final-close');
  await expect(page.locator('#closed-bar')).toBeVisible();

  // All sets: home lists this set under Finished; opening it shows its final card again
  await page.click('#home-btn');
  await expect(page.locator('#dropzone')).toBeVisible();
  await page.locator('#dropzone summary', { hasText: 'Finished' }).click();
  // exact name: NAME is also a prefix of NAME_1M, whose row exists when the tests run in parallel
  await page.locator('.set-row').filter({ has: page.locator('.set-name').getByText(NAME, { exact: true }) }).click();
  await expect(page.locator('#final')).toBeVisible({ timeout: 30000 });
  await shot('7-reopened');
  // zip contents are checked on the host by e2e.sh (no unzip in this image)
});

test('time up closes the round', async ({ page, request }) => {
  test.setTimeout(240000);
  const api = async p => (await request.get(BASE + p, { headers: H })).json();
  await page.goto(BASE);
  const bytes = Array.from(fs.readFileSync(ZIP_1M));
  const dt = await page.evaluateHandle(b => {
    const d = new DataTransfer();
    d.items.add(new File([new Uint8Array(b)], 'set.zip', { type: 'application/zip' }));
    return d;
  }, bytes);
  for (const t of ['dragenter', 'dragover', 'drop']) await page.dispatchEvent('body', t, { dataTransfer: dt });
  await expect.poll(async () => (await api('/api/sets')).sets.some(s => s.name === NAME_1M), { timeout: 30000 }).toBe(true);
  await pickSet(page, NAME_1M);
  await page.click('#start-btn');
  await expect(page.locator('#round')).toBeVisible();

  // nothing pressed: 00:00 closes and grades the round
  await expect(page.locator('#final')).toBeVisible({ timeout: 90000 });
  await expect(page.locator('#final')).toContainText("Time's up");
  await expect(page.locator('#final')).toContainText(/\d+\s*\/\s*\d+/);
  await expect(page.locator('#final .late')).toHaveCount(0);
  await page.click('#final-close');
  await expect(page.locator('#closed-bar')).toBeVisible();

  // practice after the close is marked after time
  await page.click('#submit-btn');
  await expect(page.locator('#results .late')).toBeVisible({ timeout: 180000 });

  const s = await api(`/api/sets/${NAME_1M}/state`);
  expect(s.ended).toBe(true);
  for (const g of Object.values(s.final)) expect(g.after_time).toBe(false);
  const ev = s.events.map(e => e[1]).join(' | ');
  expect(ev).toContain('time up');
  expect(ev).not.toContain('end (after time)');
});

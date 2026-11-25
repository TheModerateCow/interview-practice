import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:8766';   // the isolated test stack
const NAME = process.env.E2E_NAME;
const ZIP = process.env.E2E_ZIP;
const NAME_1M = process.env.E2E_NAME_1M;
const ZIP_1M = process.env.E2E_ZIP_1M;
const NAME_RUN = process.env.E2E_NAME_RUN;
const NAME_RACE = process.env.E2E_NAME_RACE;
const ZIP_RUN = process.env.E2E_ZIP_RUN;
const ZIP_RACE = process.env.E2E_ZIP_RACE;
const OUT = '/work/tests/out';
const REF = '/work/tests/sets/rate-limiter-py/reference';
const H = { 'X-ILab': '1' };

// The set picker is a custom dropdown: open it, then click the option for this set name.
async function pickSet(page, name) {
  await page.click('#set-picker');
  await page.click(`#set-picker-list [data-value="${name}"]`);
}

// Other tests share this stack, so a round may be running when a page loads: if the app asks before leaving it, say Open.
async function openIfAsked(page) {
  await page.locator('#drop-confirm-open').click({ timeout: 4000 }).catch(() => {});
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
  await openIfAsked(page);

  // wait for the import to land, then make sure the ready screen shows this set
  await expect.poll(async () => (await api('/api/sets')).sets.some(s => s.name === NAME), { timeout: 30000 }).toBe(true);
  const info = await api(`/api/sets/${NAME}`);
  await expect(page.locator('#ready')).toContainText(info.title);
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
  await openIfAsked(page);
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

test('a drop during page load wins, and a round in progress is asked first', async ({ page, request }) => {
  // a round in progress, so the page's own first load wants to reopen it
  const imp = await request.post(`${BASE}/api/import`, { headers: H, data: fs.readFileSync(ZIP_RUN) });
  expect(imp.ok()).toBeTruthy();
  expect((await request.post(`${BASE}/api/sets/${NAME_RUN}/start`, { headers: H })).ok()).toBeTruthy();
  const title = (await (await request.get(`${BASE}/api/sets/${NAME_RUN}/state`, { headers: H })).json()).title;
  const bytes = Array.from(fs.readFileSync(ZIP_RACE));
  const drop = async () => {
    const dt = await page.evaluateHandle(b => {
      const d = new DataTransfer();
      d.items.add(new File([new Uint8Array(b)], 'race.zip', { type: 'application/zip' }));
      return d;
    }, bytes);
    for (const t of ['dragenter', 'dragover', 'drop']) await page.dispatchEvent('body', t, { dataTransfer: dt });
  };
  const raceSet = async () => (await (await request.get(`${BASE}/api/sets`, { headers: H })).json()).sets.some(s => s.name === NAME_RACE);

  // Stay (during page load, no waiting): nothing is imported, the round comes back and stays
  await page.goto(BASE, { waitUntil: 'commit' });
  await page.waitForFunction(() => document.body);
  await drop();
  await expect(page.locator('#drop-confirm')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('#drop-confirm-stay')).toBeFocused();
  await page.screenshot({ path: `${OUT}/e2e-drop-confirm.png` });
  await page.click('#drop-confirm-stay');
  await expect(page.locator('#round')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('#drop-confirm')).toBeHidden();
  expect(await raceSet()).toBe(false);

  // Esc is Stay too
  await drop();
  await expect(page.locator('#drop-confirm')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#drop-confirm')).toBeHidden();
  await expect(page.locator('#round')).toBeVisible();
  expect(await raceSet()).toBe(false);

  // Open, during page load: the dropped set's ready screen wins and stays
  await page.goto(BASE, { waitUntil: 'commit' });
  await page.waitForFunction(() => document.body);
  await drop();
  await expect(page.locator('#drop-confirm')).toBeVisible({ timeout: 30000 });
  await page.click('#drop-confirm-open');
  await expect(page.locator('#ready')).toContainText(title, { timeout: 30000 });
  await expect(page.locator('#start-btn')).toBeVisible();
  await page.waitForTimeout(3000);
  await expect(page.locator('#ready')).toBeVisible();
  await expect(page.locator('#round')).toBeHidden();
  await expect(page.locator('#ready .err', { hasText: /\S/ })).toHaveCount(0);

  // on a ready screen a drop needs no question
  await drop();
  await expect(page.locator('#ready')).toContainText(title, { timeout: 30000 });
  await expect(page.locator('#drop-confirm')).toBeHidden();
});

test('Home: delete a finished and an unstarted set', async ({ page, request }) => {
  const A = `${NAME}-del-a`, B = `${NAME}-del-b`;   // A is finished, B is not started
  const api = async (p, o = {}) => request.fetch(BASE + p, { headers: H, ...o });
  for (const n of [A, B]) {
    const r = await api('/api/import', { method: 'POST', data: fs.readFileSync(`${OUT}/${n}.zip`) });
    expect(r.status()).toBe(200);
  }
  await api(`/api/sets/${A}/start`, { method: 'POST' });
  await api(`/api/sets/${A}/end`, { method: 'POST' });

  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  if (await page.locator('#home-btn').isVisible()) await page.click('#home-btn');
  const del = n => page.getByRole('button', { name: new RegExp(`^Delete .* \\(${n}\\)$`) });
  const row = n => page.locator('.set-name', { hasText: new RegExp(`^${n}$`) });
  await page.locator('summary', { hasText: 'Finished' }).click();   // Finished starts collapsed
  await expect(del(A)).toBeVisible();
  await expect(del(B)).toBeVisible();

  // Keep and Esc leave the row
  await del(A).click();
  await expect(page.locator('#delete-confirm')).toContainText(`(${A})? It leaves the app. Its folder moves to data/deleted/, and your exports stay in data/exports/.`);
  await expect(page.locator('#delete-confirm-no')).toBeFocused();
  await page.click('#delete-confirm-no');
  await expect(page.locator('#delete-confirm')).toBeHidden();
  await del(A).click(); await page.keyboard.press('Escape');
  await expect(page.locator('#delete-confirm')).toBeHidden();
  await expect(row(A)).toHaveCount(1);

  for (const n of [A, B]) {
    await del(n).click();
    await page.click('#delete-confirm-yes');
    await expect(page.locator('#flash')).toContainText(`Deleted `);
    await expect(page.locator('#flash')).toContainText(`(${n})`);
    await expect(row(n)).toHaveCount(0);
    expect((await api(`/api/sets/${n}`)).status()).toBe(404);
  }
  expect((await api('/api/import', { method: 'POST', data: fs.readFileSync(`${OUT}/${A}.zip`) })).status()).toBe(200);   // same zip imports again
  await api(`/api/sets/${A}`, { method: 'DELETE' });
});

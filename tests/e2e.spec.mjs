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
  // a page can open on a finished round (another test's set) with its Results card up, which covers the picker
  if (await page.locator('#final').isVisible()) await page.click('#final-close');
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
  await expect(page.locator('#flash')).toContainText('Imported');
  await expect(page.locator('#flash')).toContainText(NAME);
  // a bad drop says "Not imported" and leaves this ready screen alone
  const badBytes = Array.from(fs.readFileSync('/work/tests/sets/_zips/invalid-bad-manifest.zip'));
  const bad = await page.evaluateHandle(b => {
    const d = new DataTransfer();
    d.items.add(new File([new Uint8Array(b)], 'invalid-bad-manifest.zip', { type: 'application/zip' }));
    return d;
  }, badBytes);
  for (const t of ['dragenter', 'dragover', 'drop']) await page.dispatchEvent('body', t, { dataTransfer: bad });
  await expect(page.locator('#flash.bad')).toContainText('Not imported: invalid-bad-manifest.zip');
  await expect(page.locator('#ready')).toContainText(info.title);
  await expect(page.locator('#start-btn')).toBeVisible();
  await shot('1-ready');
  await expect(page.locator('#ready-name')).toHaveText(NAME);
  await expect(page.locator('#ready-assist')).toContainText('Python\'s standard library');   // the e2e set is Python
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
  const p1first = (await page.locator('#problem').textContent()).replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s/)[0].slice(0, 40);
  await expect(page.locator('#level-tabs')).toHaveCount(0);
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
  // Run runs the run program even with another file open
  const other = st.run_entry && st.files.find(f => f !== st.run_entry && /\.(py|go|java)$/.test(f));
  if (other) {
    await page.click(`[data-testid="file-${other}"]`);
    const [rq2] = await Promise.all([page.waitForRequest(r => r.url().includes('/run'), { timeout: 10000 }), page.click('#run-btn')]);
    expect(rq2.postDataJSON().file).toBe(st.run_entry);
    await expect(page.locator('#verdict')).toBeVisible({ timeout: 120000 });
    if (st.testcases_count > 0) await expect(page.locator('body')).toContainText(/[✓✗]/);
    await page.click(`[data-testid="file-${st.run_entry}"]`);
  }

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
  // part 2 opens in its own tab; part 1 is one click away
  const tabs = page.locator('#level-tabs .level-tab');
  await expect(page.locator('#level-tabs')).toBeVisible();
  await expect(tabs).toHaveCount(2);
  await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#problem')).not.toContainText(p1first);
  await tabs.nth(0).click();
  await expect(page.locator('#problem')).toContainText(p1first);
  await expect(page.locator('#level-panel')).not.toContainText(snippet);  // scoped: the tab itself says "Part 2"
  await tabs.nth(0).focus();
  await page.keyboard.press('ArrowRight');
  await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#problem')).toContainText(snippet);
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

test('Catalog: filter, then pick a problem to open an attempt', async ({ page, request }) => {
  const cat = await (await request.get(`${BASE}/api/catalog`, { headers: H })).json();
  const dsa = cat.problems.filter(p => p.round === 'dsa');
  const p = dsa[0];
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  if (await page.locator('#home-btn').isVisible()) await page.click('#home-btn');
  await expect(page.locator('#catalog h2')).toContainText('Problems');
  await page.click('#f-round');
  await page.click('#f-round-list [data-value="dsa"]');
  // other tests import sets in parallel (each joins the catalog), so check the filter by content, not an exact count
  await expect.poll(async () => (await page.locator('#catalog .set-meta').allTextContents()).every(t => t.startsWith('DSA round'))).toBe(true);
  expect(await page.locator('#catalog .set-row').count()).toBeGreaterThanOrEqual(dsa.length);
  await page.click(`#catalog [data-problem="${p.id}"]`);
  await expect(page.locator('#ready')).toBeVisible();
  await expect(page.locator('#ready h1')).toHaveText(p.title);
  await expect(page.locator('#ready-name')).toHaveText(new RegExp(`^${p.id}-([a-z]+-)?\\d+$`));
  await page.click('#home-btn');
  await page.click('#f-round');
  await page.click('#f-round-list [data-value=""]');   // back to all
  await expect.poll(() => page.locator('#catalog .set-row').count()).toBeGreaterThanOrEqual(cat.problems.length);
});

test('Catalog: the language you choose is the one that opens', async ({ page, request }) => {
  const cat = await (await request.get(`${BASE}/api/catalog`, { headers: H })).json();
  const p = cat.problems.find(q => q.source === 'builtin' && q.round === 'levelled' && q.languages.includes('java'));
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  if (await page.locator('#home-btn').isVisible()) await page.click('#home-btn');
  await expect(page.locator('#lang-pick [aria-pressed="true"]')).toHaveCount(1);
  await expect(page.locator('#catalog .lang-chip')).toHaveCount(0);
  await page.click('#lang-pick [data-lang="java"]');
  await expect(page.locator('#lang-pick [data-lang="java"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#lang-pick [aria-pressed="false"]')).toHaveCount(await page.locator('#lang-pick button').count() - 1);
  await expect(page.locator(`[data-problem="${p.id}"] .set-meta`)).toContainText('Java');
  await page.click(`[data-problem="${p.id}"]`);
  await expect(page.locator('.ready-card .pills')).toContainText('Java');
  await expect(page.locator('#ready-name')).toHaveText(new RegExp(`^${p.id}-java-\\d+$`));
  await expect(page.locator('#round')).toBeHidden();   // no clock yet
  // a one-language import says so and opens in its own language; the choice stays
  const imp = await request.post(`${BASE}/api/import`, { headers: H, data: fs.readFileSync(process.env.E2E_ZIP_LANG) });
  expect(imp.status()).toBe(200);
  await page.click('#home-btn');
  const mine = page.locator(`#catalog [data-problem="${process.env.E2E_NAME_LANG}"]`);
  await expect(mine.locator('.set-meta')).toContainText('Python only');
  await mine.click();
  await expect(page.locator('.ready-card .pills')).toContainText('Python');
  await page.click('#home-btn');
  await expect(page.locator('#lang-pick [data-lang="java"]')).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  if (await page.locator('#home-btn').isVisible()) await page.click('#home-btn');
  await expect(page.locator('#lang-pick [data-lang="java"]')).toHaveAttribute('aria-pressed', 'true');
  await page.focus('#lang-pick [data-lang="go"]');
  await page.keyboard.press('Enter');
  await expect(page.locator('#lang-pick [data-lang="go"]')).toHaveAttribute('aria-pressed', 'true');
  await page.setViewportSize({ width: 400, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await page.locator(`[data-problem="${p.id}"]`).boundingBox()).width).toBeGreaterThanOrEqual(340);   // 368 px less a 15 px scrollbar
  expect((await page.locator('#lang-pick').boundingBox()).height).toBeLessThan(40);
});

test('panes resize and remember', async ({ page, request }) => {
  const api = async p => (await request.get(BASE + p, { headers: H })).json();
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  const bytes = Array.from(fs.readFileSync(process.env.E2E_ZIP_PANES));
  const dt = await page.evaluateHandle(b => {
    const d = new DataTransfer();
    d.items.add(new File([new Uint8Array(b)], 'set.zip', { type: 'application/zip' }));
    return d;
  }, bytes);
  for (const t of ['dragenter', 'dragover', 'drop']) await page.dispatchEvent('body', t, { dataTransfer: dt });
  await openIfAsked(page);
  const NAME_P = process.env.E2E_NAME_PANES;
  await expect.poll(async () => (await api('/api/sets')).sets.some(s => s.name === NAME_P), { timeout: 30000 }).toBe(true);
  await pickSet(page, NAME_P);
  await page.click('#start-btn');
  await expect(page.locator('#round')).toBeVisible();
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });

  const size = async () => ({
    files: (await page.locator('#files').boundingBox()).width,
    problem: (await page.locator('#problem').boundingBox()).width,
    bottom: (await page.locator('#bottom').boundingBox()).height,
  });
  const drag = async (sel, dx, dy) => {
    const r = await page.locator(sel).boundingBox(), x = r.x + r.width / 2, y = r.y + r.height / 2;
    await page.mouse.move(x, y); await page.mouse.down();
    await page.mouse.move(x + dx / 2, y + dy / 2, { steps: 4 }); await page.mouse.move(x + dx, y + dy, { steps: 4 });
    await page.mouse.up();
  };
  const near = (got, want) => expect(Math.abs(got - want)).toBeLessThanOrEqual(2);
  for (const id of ['files', 'problem', 'bottom']) await expect(page.locator('#split-' + id)).toHaveAttribute('role', 'separator');

  // each border follows the pointer
  const a = await size();
  await drag('#split-files', 60, 0);
  await drag('#split-problem', -60, 0);
  await drag('#split-bottom', 0, -60);
  const b = await size();
  near(b.files, a.files + 60); near(b.problem, a.problem + 60); near(b.bottom, a.bottom + 60);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  // keyboard: ArrowRight on Files is +16 px
  await page.focus('#split-files');
  await page.keyboard.press('ArrowRight');
  near((await size()).files, b.files + 16);
  await expect(page.locator('#split-files')).toHaveAttribute('aria-valuenow', String(Math.round(b.files + 16)));

  // limits: Files never under 120 px, the bottom area never covers the editor
  await drag('#split-files', -600, 0);
  near((await size()).files, 120);
  await page.focus('#split-bottom');
  await page.keyboard.press('End');
  const col = (await page.locator('#editor-wrap').boundingBox()).height;
  expect((await size()).bottom).toBeLessThanOrEqual(0.7 * col + 2);
  await page.keyboard.press('ArrowDown');
  const d = await size();

  // the sizes survive a reload; double-click resets one
  await page.reload();
  await expect(page.locator('#round')).toBeVisible();
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  const e = await size();
  near(e.files, d.files); near(e.problem, d.problem); near(e.bottom, d.bottom);
  await page.dblclick('#split-problem');
  near((await size()).problem, 360);
});

test('Settings: word wrap, mid-round, and the clock keeps running', async ({ page, request }) => {
  const a = await (await request.post(`${BASE}/api/catalog/fares-tdd/attempt`, { headers: H, data: { language: 'java' } })).json();
  await request.post(`${BASE}/api/sets/${a.name}/start`, { headers: H, data: {} });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await pickSet(page, a.name);
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  await page.locator('#file-tree div', { hasText: 'Fares.java' }).first().click();
  // the line holding "senior" ends right of the editor box (no wrap) or inside it (wrap)
  const seniorRight = async () => page.evaluate(() => {
    const l = [...document.querySelectorAll('#editor .view-line')].find(e => e.textContent.includes('"senior"'));
    return l ? [...l.querySelectorAll('span > span')].reduce((m, s) => Math.max(m, s.getBoundingClientRect().right), 0) : -1;
  });
  const editorRight = async () => (await page.locator('#editor').boundingBox()).x + (await page.locator('#editor').boundingBox()).width;
  await expect.poll(seniorRight).toBeGreaterThan(await editorRight());
  const t1 = await page.locator('#timer').textContent();
  await page.click('#settings-btn');
  await expect(page.locator('#settings')).toBeVisible();
  await expect(page.locator('#settings-btn')).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#timer')).toBeVisible();
  await page.click('#wrap-pick [data-wrap="on"]');
  await expect(page.locator('#wrap-pick [data-wrap="on"]')).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(async () => { const r = await seniorRight(); return r > 0 && r <= await editorRight(); }).toBe(true);
  await page.waitForTimeout(2000);
  expect(await page.locator('#timer').textContent()).not.toBe(t1);   // the clock ticked while Settings was open
  await page.keyboard.press('Escape');
  await expect(page.locator('#settings')).toBeHidden();
  await expect(page.locator('#round')).toBeVisible();
  await expect(page.locator('#settings-btn')).toBeFocused();
  await expect(page.locator('#file-tree div.sel')).toHaveText('Fares.java');
  await page.reload();
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  await page.locator('#file-tree div', { hasText: 'Fares.java' }).first().click();
  await expect.poll(async () => { const r = await seniorRight(); return r > 0 && r <= await editorRight(); }).toBe(true);
  await page.click('#settings-btn');
  await expect(page.locator('#wrap-pick [data-wrap="on"]')).toHaveAttribute('aria-pressed', 'true');
  // the theme switch lives in Settings now
  await expect(page.locator('#top [data-t]')).toHaveCount(0);
  await expect(page.locator('#settings [data-t]')).toHaveCount(3);
  await page.click('#settings [data-t="dark"]');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.click('#settings-btn');
  await page.click('#settings [data-t=""]');   // back to Auto, so later tests are unaffected
  // Timer: Hide takes the countdown off the header (the round keeps running), and stays hidden after a reload
  await page.click('#timer-pick [data-timer="hidden"]');
  await expect(page.locator('#timer-pick [data-timer="hidden"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#timer')).toHaveCount(0);
  await expect(page.locator('#timer-hidden')).toHaveText('Timer hidden');
  await expect(page.locator('#top')).not.toContainText('min left');   // the set picker doesn't give the time away either
  await page.reload();
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await expect(page.locator('#timer-hidden')).toBeVisible();
  await expect(page.locator('#timer')).toHaveCount(0);
  await page.click('#settings-btn');
  await page.click('#timer-pick [data-timer="shown"]');
  await expect(page.locator('#timer')).toBeVisible();
  // 400 px: no sideways scroll, Done in view
  await page.setViewportSize({ width: 400, height: 800 });
  await expect(page.locator('#settings')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('#settings-close')).toBeInViewport();
  await expect(page.locator('#settings-btn')).toBeVisible();
  // navigating closes Settings
  await page.click('#home-btn');
  await expect(page.locator('#settings')).toBeHidden();
  await expect(page.locator('#catalog')).toBeVisible();
});

// One language server runs per app, so the code-help tests must not overlap: run them one after the other.
test.describe.serial('Code help', () => {
test('Code help: Python suggestions, hints and underlines', async ({ page, request }) => {
  const a = await (await request.post(`${BASE}/api/catalog/ledger-codebase/attempt`, { headers: H, data: { language: 'python' } })).json();
  await request.post(`${BASE}/api/sets/${a.name}/start`, { headers: H, data: {} });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await pickSet(page, a.name);
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  // main.py is open. Put the cursor on a new line inside handle(), before its last line.
  const newLine = () => page.evaluate(() => {
    const e = window.monaco.editor.getEditors()[0], m = e.getModel(), i = m.getLinesContent().findIndex(l => l.includes('return ["ok"]'));
    e.executeEdits('t', [{ range: new window.monaco.Range(i + 1, 1, i + 1, 1), text: '\n' }]); e.setPosition({ lineNumber: i + 1, column: 1 }); e.focus();
  });
  const clear = async () => { await page.keyboard.press('Escape'); await page.keyboard.press('End'); await page.keyboard.press('Shift+Home'); await page.keyboard.press('Shift+Home'); await page.keyboard.press('Delete'); };
  const row = t => page.locator(`.suggest-widget .monaco-list-row[aria-label="${t}"]`);
  await page.click('#editor .view-lines');
  await page.keyboard.press('Control+Home'); await page.keyboard.type('import heapq\n');
  await page.keyboard.press('Escape');
  // the first request starts the server; while it does, the line says so and typing is not blocked
  await expect.poll(async () => (await request.post(`${BASE}/api/sets/${a.name}/assist`, { headers: H, data: { op: 'complete', file: 'main.py', text: '' } })).json().then(j => j.state), { timeout: 30000 }).toBe('ready');
  await newLine(); await page.keyboard.type('    heapq.heap');
  await expect(row('heappush')).toBeVisible({ timeout: 5000 });
  await clear();
  await page.keyboard.type('    l.bal');
  await expect(row('balance_at')).toBeVisible({ timeout: 5000 });   // ledger/ledger.py was never opened
  await clear();
  await page.keyboard.type('    heapq.heappush(');
  await expect(page.locator('.parameter-hints-widget')).toContainText('heap', { timeout: 5000 });
  await clear();
  await page.keyboard.type('    undefined_name()'); await page.keyboard.press('Escape');   // a codebase round: names are checked, types are not
  await expect.poll(() => page.locator('.squiggly-error, .squiggly-warning').count(), { timeout: 5000 }).toBeGreaterThan(0);
  await expect(page.locator('#assist-status')).toHaveText('');
  // reload: still works
  await page.reload();
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  await page.click('#editor .view-lines');
  await newLine(); await page.keyboard.type('    l.bal');
  await expect(row('balance_at')).toBeVisible({ timeout: 15000 });
});

test('Code help: Go suggestions and underlines', async ({ page, request }) => {
  const a = await (await request.post(`${BASE}/api/catalog/ledger-codebase/attempt`, { headers: H, data: { language: 'go' } })).json();
  await request.post(`${BASE}/api/sets/${a.name}/start`, { headers: H, data: {} });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(BASE);
  await page.waitForLoadState('networkidle');
  await openIfAsked(page);
  await pickSet(page, a.name);
  await expect(page.locator('#editor .monaco-editor')).toBeVisible({ timeout: 60000 });
  await expect.poll(async () => (await request.post(`${BASE}/api/sets/${a.name}/assist`, { headers: H, data: { op: 'complete', file: 'cmd/run/main.go', text: '' } })).json().then(j => j.state), { timeout: 30000 }).toBe('ready');
  // cmd/run/main.go is open. Put the cursor on a new line before `switch {`, inside the command loop.
  await page.evaluate(() => {
    const e = window.monaco.editor.getEditors()[0], m = e.getModel(), i = m.getLinesContent().findIndex(l => l.trim().startsWith('switch {'));
    e.executeEdits('t', [{ range: new window.monaco.Range(i + 1, 1, i + 1, 1), text: '\n' }]); e.setPosition({ lineNumber: i + 1, column: 1 }); e.focus();
  });
  await page.keyboard.type('l.Bal');
  await expect(page.locator('.suggest-widget .monaco-list-row[aria-label="BalanceAt"]')).toBeVisible({ timeout: 5000 });   // ledger.go was never opened
  await page.keyboard.press('Escape');
  await page.keyboard.press('Shift+Home'); await page.keyboard.press('Delete');
  await page.keyboard.type('_ = l.Balance("a")'); await page.keyboard.press('Escape');
  await expect.poll(() => page.locator('.squiggly-error').count(), { timeout: 5000 }).toBeGreaterThan(0);
  await expect(page.locator('#assist-status')).toHaveText('');
});
});

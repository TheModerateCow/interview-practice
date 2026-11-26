// The round in progress: server state, clock, files + Monaco, and every toolbar action.
import { tick as flush } from 'svelte';
import { api, enc } from '../../lib/api.js';
import { mmss, partName } from '../../lib/util.js';
import { langOf, loadMonaco } from '../../lib/monaco.js';
import { app, showFlash } from '../../app.svelte.js';

const unlockedMsg = tag => partName(tag) + ' unlocked. It\'s open in the problem pane.';

export const round = $state({
  st: null,              // round state from the server
  deadline: 0, now: Date.now(),
  curFile: null,
  results: null,         // results pane: null | {kind: 'empty' | 'loading' | 'err' | 'run' | 'grades', ...}
  finalOpen: false,
  busy: '',              // label of the running action; '' when idle
  edReady: false,        // Monaco has loaded
  saveStatus: '',
  askNext: false, askEnd: false,
  stdin: '',
});

// Plain variables: not shown, or Monaco objects that must not be wrapped in $state.
let editorEl = null, ed = null, models = {}, dirty = false, saveT, pollT, tickT;
let closing = false, closeTry = 0, closeErr = false;

export const setEditorEl = el => { editorEl = el; };
export const isDirty = () => dirty;

// Seconds left; frozen at the close.
export function secondsLeft() {
  const st = round.st;
  return !st ? 0 : st.ended ? Math.ceil(st.left_s) : Math.max(0, Math.ceil((round.deadline - round.now) / 1000));
}
export const closedAt = () => mmss(Math.max(0, round.st.minutes * 60 - round.st.left_s));
export const openFinal = () => { if (round.st) round.finalOpen = true; };
export const closeFinal = () => { round.finalOpen = false; };

// ---------- files and Monaco
const editor = () => loadMonaco(editorEl, {
  change: () => { dirty = true; round.saveStatus = 'Unsaved'; clearTimeout(saveT); saveT = setTimeout(save, 800); },
  run: () => doRun(),
  submit: () => doSubmit(),
}).then(e => { ed = e; round.edReady = true; });

export async function openFile(p) {
  await save();
  const set = app.cur;
  const text = await (await api('/sets/' + set + '/files/' + enc(p), {}, true)).text();
  await editor();
  if (set !== app.cur) return;   // the user went elsewhere while this loaded
  const monaco = window.monaco;
  if (models[p]) models[p].dispose();
  models[p] = monaco.editor.createModel(text, langOf(p), monaco.Uri.parse('inmemory:///' + enc(p)));
  round.curFile = p; dirty = false;
  ed.setModel(models[p]);
  round.saveStatus = 'Saved';
}

export async function save() {
  clearTimeout(saveT);
  const f = round.curFile;
  if (!dirty || !f || !models[f]) return;
  dirty = false;
  try {
    await api('/sets/' + app.cur + '/files/' + enc(f), { method: 'PUT', body: models[f].getValue() });
    round.saveStatus = 'Saved';
  } catch (e) { dirty = true; round.saveStatus = 'Save failed: ' + e.message; }
}

// created() runs once the file exists on the server, before it opens.
export async function addFile(path, created) {
  const p = path.trim().replace(/^\/+/, ''); if (!p) return;
  await api('/sets/' + app.cur + '/files/' + enc(p), { method: 'PUT', body: '' });
  created();
  if (!round.st.files.includes(p)) round.st.files.push(p);
  await openFile(p);
}

// ---------- entering and leaving
export function stopTimers() { clearInterval(pollT); clearInterval(tickT); }

// Save, then drop everything that belongs to the current set.
export async function leaveRound() {
  await save();
  round.finalOpen = false; round.askNext = false; round.askEnd = false;
  Object.values(models).forEach(m => m.dispose()); models = {}; round.curFile = null; round.st = null;
  round.results = null;
}

// The caller has already switched to the round screen. `my` is the navigation this belongs to.
export async function enterRound(s, my) {
  round.st = null; round.results = { kind: 'empty' };
  setState(s);
  await flush();   // the round screen is visible before Monaco measures its box
  await editor(); if (my !== app.nav) return;
  const st = round.st;
  const first = st.files.find(f => f === st.run_entry) || st.files[0];
  if (first) await openFile(first);
  if (my !== app.nav) return;
  stopTimers();
  pollT = setInterval(poll, 5000); tickT = setInterval(clockTick, 250); clockTick();
  if (round.st.ended) openFinal();
}

export function setState(s) {
  round.st = s;
  round.deadline = Date.now() + s.left_s * 1000;   // server "now" cancels out: left_s is relative to it
  const o = app.sets.find(x => x.name === app.cur);
  if (o) { o.title = s.title; o.status = s.status; o.left_s = s.left_s; }
}

async function poll() {
  if (!app.cur) return;
  try {
    const s = await api('/sets/' + app.cur + '/state');
    if (s.name === app.cur || !s.name) { const wasEnded = round.st && round.st.ended; setState(s); if (s.ended && !wasEnded) openFinal(); }
  } catch (e) {}
}

function clockTick() {
  if (!round.st) return;
  round.now = Date.now();
  if (secondsLeft() === 0 && !round.st.ended) autoClose();
}

// 00:00 closes the round: save, then the same call as End. Retries on the next tick after 5 s if it fails.
async function autoClose() {
  if (closing || round.busy || Date.now() - closeTry < 5000) return;
  closing = true; closeTry = Date.now(); const name = app.cur;
  round.busy = 'Time is up: running hidden tests one last time';
  try {
    await save();
    const s = await api('/sets/' + name + '/end', { method: 'POST' });
    if (name !== app.cur) return;
    closeErr = false; setState(s); openFinal();
  } catch (e) {
    if (name === app.cur && !closeErr) { closeErr = true; round.results = { kind: 'err', msg: 'Time is up but the round could not be closed: ' + e.message + ' Retrying.' }; }
  } finally { closing = false; round.busy = ''; }
}

// ---------- actions: one at a time, after a save; errors land in the results pane
export async function guarded(label, fn) {
  if (round.busy || !round.st) return;
  round.busy = label;
  try { await save(); await fn(); }
  catch (e) { round.results = { kind: 'err', msg: e.message }; }
  finally { round.busy = ''; }
}

export function doRun() {
  guarded('Running', async () => {
    const file = round.st.run_entry || round.curFile;   // Run runs the run program, whichever tab is open
    round.results = { kind: 'loading', msg: 'Running ' + (file || 'your code') };
    const r = await api('/sets/' + app.cur + '/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file, stdin: round.stdin }) });
    round.results = { kind: 'run', r, late: !!round.st.ended, stdin: round.stdin };
  });
}

export function doMyTests() {
  guarded('Running your tests', async () => {
    round.results = { kind: 'loading', msg: 'Running your tests' };
    const g = await api('/sets/' + app.cur + '/mytests', { method: 'POST' });
    round.results = { kind: 'grades', title: 'My tests', rows: { 'my tests': g }, names: true };
  });
}

export function doSubmit() {
  if (!round.st || !round.st.has_submit) return;
  guarded('Submitting', async () => {
    const was = round.st.ended;
    round.results = { kind: 'loading', msg: 'Running hidden tests' };
    const r = await api('/sets/' + app.cur + '/submit', { method: 'POST' });
    round.results = { kind: 'grades', title: 'Hidden tests', rows: r.results, names: false };
    setState(r.state);
    if ((r.revealed || []).length) showFlash(unlockedMsg(round.st.unlocked[round.st.unlocked.length - 1]));
    if (r.state.ended && !was) openFinal();
  });
}

export async function doExport() {
  await save();
  const r = await api('/sets/' + app.cur + '/export', {}, true);
  const u = URL.createObjectURL(await r.blob());
  const a = document.createElement('a'); a.href = u; a.download = 'export.zip'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 10000);
  showFlash('Downloaded export.zip. Send it to Claude for the debrief. A copy is in data/exports/.');
}

export function nextPart() {
  round.askNext = false;
  guarded('Revealing the next part', async () => {
    const before = (round.st.parts || []).length;
    setState(await api('/sets/' + app.cur + '/next', { method: 'POST' }));
    if (round.st.parts.length > before) showFlash(unlockedMsg(round.st.unlocked[round.st.parts.length]));
  });
}

export function endRound() {
  round.askEnd = false;
  guarded('Ending: running hidden tests one last time', async () => { setState(await api('/sets/' + app.cur + '/end', { method: 'POST' })); openFinal(); });
}

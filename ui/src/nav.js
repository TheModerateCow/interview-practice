// Navigation between Home / Ready / Round. Every step bumps or checks app.nav, so only the latest navigation lands.
import { api } from './lib/api.js';
import { LS } from './lib/util.js';
import { app, fetchSets } from './app.svelte.js';
import { enterRound, leaveRound, stopTimers } from './features/round/round.svelte.js';

function screen(v) {
  app.settings = false;
  app.view = v;
  if (v !== 'round') stopTimers();
}

// The round a page load resumes: the last one opened if it's still running, else any running one.
export function resumable(sets) {
  const running = sets.filter(s => s.status === 'running').map(s => s.name), last = LS.get('ilab-last');
  return running.includes(last) ? last : running[0];
}

export async function refreshSets(my = app.nav) {
  const fresh = await fetchSets();
  if (my === app.nav) app.sets = fresh;
}

// First load, and after an import or a catalog pick: open `select`, else resume a running round, else Home.
export async function loadSets(select, my = app.nav) {
  app.sets = await fetchSets();
  if (my !== app.nav) return;
  if (select && app.sets.some(s => s.name === select)) return openSet(select);
  const resume = resumable(app.sets);
  return resume ? openSet(resume) : goHome();
}

export const boot = () => loadSets().catch(e => { screen('home'); app.dropErr = e.message; });

// Save, then drop everything that belongs to the current set.
async function leaveSet() {
  await leaveRound();
  app.ready = null; app.readyErr = '';
}

export async function goHome() {
  const my = ++app.nav;
  await leaveSet(); if (my !== app.nav) return;
  app.cur = null; app.loading = ''; screen('home');
  try { await refreshSets(my); } catch (e) {}   // fresh statuses: rounds may have timed out
}

export async function openSet(name, my = ++app.nav) {
  await leaveSet(); if (my !== app.nav) return;
  app.cur = name; LS.set('ilab-last', name);
  screen(''); app.loading = 'Opening ' + (app.sets.find(s => s.name === name)?.title || name);
  try {
    const i = await api('/sets/' + name); if (my !== app.nav) return;
    if (i.status === 'ready') { app.ready = i; screen('ready'); return; }
    const s = await api('/sets/' + name + '/state'); if (my !== app.nav) return;
    screen('round'); await enterRound(s, my);
  } catch (e) { if (my === app.nav) { screen('ready'); app.readyErr = e.message; } }
  finally { if (my === app.nav) app.loading = ''; }
}

export async function startRound() {   // errors go back to the ready screen's Start button
  const s = await api('/sets/' + app.cur + '/start', { method: 'POST' });
  const my = ++app.nav;
  screen('round'); await enterRound(s, my);
}

<script>
  // The shell: header, navigation between Home / Ready / Round, toasts. Each screen lives in features/.
  import { onMount } from 'svelte';
  import Dropdown from './components/Dropdown.svelte';
  import Settings from './features/settings/Settings.svelte';
  import Home from './features/home/Home.svelte';
  import Ready from './features/ready/Ready.svelte';
  import Round from './features/round/Round.svelte';
  import Clock from './features/round/Clock.svelte';
  import DropImport from './features/import/DropImport.svelte';
  import Health from './features/health/Health.svelte';
  import { api } from './lib/api.js';
  import { LS, statusWords } from './lib/util.js';
  import { app, fetchSets } from './app.svelte.js';
  import { enterRound, leaveRound, stopTimers } from './features/round/round.svelte.js';

  let info = $state(null);          // ready screen
  let readyErr = $state('');
  let loading = $state('Loading sets');   // page-level wait while no screen is shown

  function screen(v) {
    app.settings = false;
    app.view = v;
    if (v !== 'round') stopTimers();
  }

  async function loadSets(select, my = app.nav) {   // first load, and after an import
    app.sets = await fetchSets();
    if (my !== app.nav) return;
    if (select && app.sets.some(s => s.name === select)) return openSet(select);   // just imported
    // A round in progress resumes (a reload mid-round lands back in it); otherwise start at home.
    const running = app.sets.filter(s => s.status === 'running').map(s => s.name);
    const resume = running.includes(LS.get('ilab-last')) ? LS.get('ilab-last') : running[0];
    if (resume) return openSet(resume);
    return goHome();
  }

  // Save, then drop everything that belongs to the current set.
  async function leaveSet() {
    await leaveRound();
    info = null; readyErr = '';
  }

  async function goHome() {
    const my = ++app.nav;
    await leaveSet(); if (my !== app.nav) return;
    app.cur = null; loading = ''; screen('home');
    try { const fresh = await fetchSets(); if (my === app.nav) app.sets = fresh; } catch (e) {}   // fresh statuses: rounds may have timed out
  }

  async function openSet(name, my = ++app.nav) {
    await leaveSet(); if (my !== app.nav) return;
    app.cur = name; LS.set('ilab-last', name);
    screen(''); loading = 'Opening ' + (app.sets.find(s => s.name === name)?.title || name);
    try {
      const i = await api('/sets/' + name); if (my !== app.nav) return;
      if (i.status === 'ready') { info = i; screen('ready'); return; }
      const s = await api('/sets/' + name + '/state'); if (my !== app.nav) return;
      screen('round'); await enterRound(s, my);
    } catch (e) { if (my === app.nav) { screen('ready'); readyErr = e.message; } }
    finally { if (my === app.nav) loading = ''; }
  }

  async function startRound() {   // errors go back to the ready screen's Start button
    const s = await api('/sets/' + app.cur + '/start', { method: 'POST' });
    const my = ++app.nav;
    screen('round'); await enterRound(s, my);
  }

  onMount(() => { loadSets().catch(e => { screen('home'); app.dropErr = e.message; }); });
</script>

<header id="top" class:above={app.settings}>
  <strong class="brand">Interview Lab</strong>
  <button id="home-btn" class="btn btn-ghost" class:hidden={!app.view || app.view === 'home'} type="button" onclick={goHome}>All sets</button>
  {#if app.sets.length && app.view !== 'home'}
    <Dropdown id="set-picker" label="Interview set" value={app.cur} onchange={openSet}
      options={app.sets.map(s => ({ value: s.name, label: s.title, meta: s.name + ' · ' + statusWords(s, app.hideTimer) }))} />
  {/if}
  <span class="spacer"></span>
  <Clock shown={app.view === 'round'} />
  <button id="settings-btn" class="btn btn-ghost" type="button" aria-expanded={app.settings}
    aria-controls="settings" onclick={() => (app.settings = !app.settings)}>Settings</button>
</header>
<DropImport reload={loadSets} reopen={() => (app.cur ? openSet(app.cur) : loadSets())} />
<Health />
{#if !app.view && loading}<div class="loading block" role="status">{loading}…</div>{/if}

<Home onopen={openSet} onpick={name => loadSets(name)} />
<Ready shown={app.view === 'ready'} {info} err={readyErr} onstart={startRound} />
<Round />
<Settings />

{#if app.importing}<div class="toast" role="status"><span class="loading">Importing {app.importing}…</span></div>{/if}
{#key app.flash.n}<div id="flash" class="toast" class:hidden={!app.flash.on} class:bad={app.flash.bad} role="status">{app.flash.text}</div>{/key}

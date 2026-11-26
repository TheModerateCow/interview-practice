<script>
  // The shell: header, the screens (each in features/), toasts. Navigation lives in nav.js.
  import { onMount } from 'svelte';
  import Dropdown from './components/Dropdown.svelte';
  import Settings from './features/settings/Settings.svelte';
  import Home from './features/home/Home.svelte';
  import Ready from './features/ready/Ready.svelte';
  import Round from './features/round/Round.svelte';
  import Clock from './features/round/Clock.svelte';
  import DropImport from './features/import/DropImport.svelte';
  import Health from './features/health/Health.svelte';
  import { statusWords } from './lib/util.js';
  import { app } from './app.svelte.js';
  import { boot, goHome, openSet } from './nav.js';

  onMount(boot);
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
  <button id="settings-btn" class="btn btn-ghost icon-btn" type="button" aria-label="Settings" title="Settings" aria-expanded={app.settings}
    aria-controls="settings" onclick={() => (app.settings = !app.settings)}><svg class="gear" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="6.8"/><circle cx="12" cy="12" r="2.6"/><g stroke-width="3.4"><line x1="18.28" y1="14.60" x2="20.87" y2="15.67"/><line x1="14.60" y1="18.28" x2="15.67" y2="20.87"/><line x1="9.40" y1="18.28" x2="8.33" y2="20.87"/><line x1="5.72" y1="14.60" x2="3.13" y2="15.67"/><line x1="5.72" y1="9.40" x2="3.13" y2="8.33"/><line x1="9.40" y1="5.72" x2="8.33" y2="3.13"/><line x1="14.60" y1="5.72" x2="15.67" y2="3.13"/><line x1="18.28" y1="9.40" x2="20.87" y2="8.33"/></g></svg></button>
</header>
<DropImport />
<Health />
{#if !app.view && app.loading}<div class="loading block" role="status">{app.loading}…</div>{/if}

<Home />
<Ready />
<Round />
<Settings />

{#if app.importing}<div class="toast" role="status"><span class="loading">Importing {app.importing}…</span></div>{/if}
{#key app.flash.n}<div id="flash" class="toast" class:hidden={!app.flash.on} class:bad={app.flash.bad} role="status">{app.flash.text}</div>{/key}

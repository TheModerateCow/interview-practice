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
  import { onTop } from './lib/dialog.js';
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
  <button id="settings-btn" class="btn btn-ghost" type="button" aria-expanded={app.settings}
    aria-controls="settings" onclick={() => (app.settings = !app.settings)}>Settings</button>
</header>
<DropImport />
<Health />
{#if !app.view && app.loading}<div class="loading block" role="status">{app.loading}…</div>{/if}

<Home />
<Ready />
<Round />
<Settings />

{#if app.importing}<div class="toast" role="status" popover="manual" use:onTop><span class="loading">Importing {app.importing}…</span></div>{/if}
{#key app.flash.n}<div id="flash" class="toast" popover="manual" use:onTop class:hidden={!app.flash.on} class:bad={app.flash.bad} role="status">{app.flash.text}</div>{/key}

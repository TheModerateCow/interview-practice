<script>
  // Home: rounds in progress, the problem catalog, past attempts (Not started / Finished, with Delete), and the drop hint.
  import { tick as flush } from 'svelte';
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, statusWords } from '../../lib/util.js';
  import { app, showFlash } from '../../app.svelte.js';
  import { openSet, refreshSets } from '../../nav.js';
  import Catalog from '../catalog/Catalog.svelte';

  let delSet = $state(null), delNoEl = $state();   // the row whose Delete confirm is open, and its Keep button

  async function askDelete(s) { delSet = s; await flush(); delNoEl.focus(); }
  async function doDelete() {
    const s = delSet, my = app.nav; delSet = null;
    try {
      await api('/sets/' + s.name, { method: 'DELETE' });
      if (LS.get('ilab-last') === s.name) LS.set('ilab-last', '');
      await refreshSets(my);
      showFlash(`Deleted ${s.title} (${s.name})`);
    } catch (e) { showFlash(e.message, true); }
  }
</script>

<svelte:window onkeydown={e => { if (e.key === 'Escape' && delSet) delSet = null; }} />

{#snippet group(status, label)}
  {@const list = app.sets.filter(s => s.status === status)}
  {#if list.length}
    <details class="sets" open={status !== 'ended'}>
      <summary class="label">{label} · {list.length}</summary>
      {#each list as s (s.name)}
        <div class="set-item">
          <button type="button" class="set-row" onclick={() => openSet(s.name)}>
            <span class="set-title">{s.title}</span>
            <span class="set-meta">{[ROUND[s.round] || s.round, LANGNAME[s.language] || s.language, status === 'running' && statusWords(s, app.hideTimer)].filter(Boolean).join(' · ')}</span>
            <span class="set-name">{s.name}</span>
          </button>
          {#if status !== 'running'}<button type="button" class="set-del" aria-label="Delete {s.title} ({s.name})" onclick={() => askDelete(s)}>Delete</button>{/if}
        </div>
      {/each}
    </details>
  {/if}
{/snippet}

<main id="dropzone" class:hidden={app.view !== 'home'} class:over={app.over}>
  <div class="home">
    {@render group('running', 'In progress')}
    <Catalog />
    {@render group('ready', 'Not started')}
    {@render group('ended', 'Finished')}
    <div class="drop">
      <p class="drop-line">Have a set from Claude? Drop its .zip anywhere on this page. It's added to your problems.</p>
      <p id="drop-error" class="err" role="alert">{app.dropErr}</p>
    </div>
  </div>
</main>

<div id="delete-confirm" class="overlay" class:hidden={!delSet} role="dialog" aria-modal="true" aria-label="Delete set">
  {#if delSet}
    <div class="final-card">
      <p>Delete {delSet.title} ({delSet.name})? It leaves the app. Its folder moves to data/deleted/, and your exports stay in data/exports/.</p>
      <div class="actions"><button id="delete-confirm-yes" class="btn btn-danger strong" type="button" onclick={doDelete}>Delete</button>
        <button id="delete-confirm-no" bind:this={delNoEl} class="btn btn-ghost" type="button" onclick={() => (delSet = null)}>Keep</button></div>
    </div>
  {/if}
</div>

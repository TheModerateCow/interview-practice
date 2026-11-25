<script>
  // Home: the drop zone, the sets grouped In progress / Not started / Finished with Delete, then the preset Library.
  import { tick as flush } from 'svelte';
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, statusWords } from '../../lib/util.js';
  import { app, fetchSets, showFlash } from '../../app.svelte.js';
  import Library from '../library/Library.svelte';
  let { onopen, ontake } = $props();

  const GROUPS = [['running', 'In progress'], ['ready', 'Not started'], ['ended', 'Finished']];
  let delSet = $state(null), delNoEl = $state();   // the row whose Delete confirm is open, and its Keep button

  async function askDelete(s) { delSet = s; await flush(); delNoEl.focus(); }
  async function doDelete() {
    const s = delSet, my = app.nav; delSet = null;
    try {
      await api('/sets/' + s.name, { method: 'DELETE' });
      if (LS.get('ilab-last') === s.name) LS.set('ilab-last', '');
      const fresh = await fetchSets(); if (my === app.nav) app.sets = fresh;
      showFlash(`Deleted ${s.title} (${s.name})`);
    } catch (e) { showFlash(e.message, true); }
  }
</script>

<svelte:window onkeydown={e => { if (e.key === 'Escape' && delSet) delSet = null; }} />

<main id="dropzone" class:hidden={app.view !== 'home'} class:over={app.over}>
  <div class="home">
    <div class="drop">
      <h1 class="drop-big">Drop a set .zip here</h1>
      <p>Sets come from Claude's interview-practice skill. Drag the .zip anywhere onto this page.</p>
      <p id="drop-error" class="err" role="alert">{app.dropErr}</p>
    </div>
    {#each GROUPS as [status, label]}
      {@const list = app.sets.filter(s => s.status === status)}
      {#if list.length}
        <details class="sets" open={status !== 'ended'}>
          <summary class="label">{label} · {list.length}</summary>
          {#each list as s (s.name)}
            <div class="set-item">
              <button type="button" class="set-row" onclick={() => onopen(s.name)}>
                <span class="set-title">{s.title}</span>
                <span class="set-meta">{[ROUND[s.round] || s.round, LANGNAME[s.language] || s.language, status === 'running' && statusWords(s)].filter(Boolean).join(' · ')}</span>
                <span class="set-name">{s.name}</span>
              </button>
              {#if status !== 'running'}<button type="button" class="set-del" aria-label="Delete {s.title} ({s.name})" onclick={() => askDelete(s)}>Delete</button>{/if}
            </div>
          {/each}
        </details>
      {/if}
    {/each}
    <Library {ontake} />
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

<script>
  // Home: rounds in progress, the problem catalog, past attempts (Not started / Finished, with Delete), and the drop hint.
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, statusWords } from '../../lib/util.js';
  import { app, showFlash } from '../../app.svelte.js';
  import { openSet, refreshSets } from '../../nav.js';
  import { modal } from '../../lib/dialog.js';
  import Catalog from '../catalog/Catalog.svelte';

  let delSet = $state(null);   // the row whose Delete confirm is open

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
          {#if status !== 'running'}<button type="button" class="set-del" aria-label="Delete {s.title} ({s.name})" onclick={() => (delSet = s)}>Delete</button>{/if}
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

<dialog id="delete-confirm" class="overlay" aria-label="Delete set" use:modal={!!delSet} onclose={() => (delSet = null)}>
  {#if delSet}
    <div class="final-card">
      <p>Delete {delSet.title} ({delSet.name})? It leaves the app. Its folder moves to data/deleted/, and your exports stay in data/exports/.</p>
      <div class="actions"><button id="delete-confirm-yes" class="btn btn-danger strong" type="button" onclick={doDelete}>Delete</button>
        <!-- svelte-ignore a11y_autofocus (a dialog's safe default: Keep) -->
        <button id="delete-confirm-no" autofocus class="btn btn-ghost" type="button" onclick={() => (delSet = null)}>Keep</button></div>
    </div>
  {/if}
</dialog>

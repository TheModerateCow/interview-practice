<script>
  // Drag & drop import, the only import path: a .zip dropped anywhere on the page.
  import { tick as flush } from 'svelte';
  import { api } from '../../lib/api.js';
  import { app, fetchSets, showFlash } from '../../app.svelte.js';
  import { round } from '../round/round.svelte.js';
  import { loadSets, openSet, resumable } from '../../nav.js';

  let askDrop = $state(null), stayEl, dragN = 0;
  $effect(() => { document.body.classList.toggle('over', app.over); });

  const hasFiles = e => e.dataTransfer && [...(e.dataTransfer.types || [])].includes('Files');
  function onDragEnter(e) { if (hasFiles(e)) { e.preventDefault(); dragN++; app.over = true; } }
  function onDragOver(e) { if (hasFiles(e)) e.preventDefault(); }
  function onDragLeave(e) { if (hasFiles(e) && --dragN <= 0) { dragN = 0; app.over = false; } }

  // A round in progress: the open (or still opening) set is started and not closed. Anything else needs no question.
  async function roundRunning() {
    if (app.view === 'round' && round.st) return !round.st.ended;
    if (app.view === 'ready' || app.view === 'home') return false;
    try {   // still opening: the page's first load may not know yet, so ask the server
      const sets = await fetchSets();
      return app.cur ? sets.some(s => s.name === app.cur && s.status === 'running') : !!resumable(sets);
    } catch (e) { return false; }
  }
  async function onDrop(e) {
    e.preventDefault(); dragN = 0; app.over = false;
    const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (!f) return;
    if (await roundRunning()) { askDrop = f; await flush(); stayEl.focus(); return; }
    return doImport(f);
  }
  const dropOpen = () => { const f = askDrop; askDrop = null; return doImport(f); };

  async function doImport(f) {
    app.dropErr = ''; app.importing = f.name;
    const my = ++app.nav;   // a first load still in flight never lands on top of the drop
    try {
      const { name, title, replaced } = await api('/import', { method: 'POST', body: await f.arrayBuffer() });
      app.importing = '';
      showFlash('Imported ' + title + ' (' + name + ')' + (replaced ? ", replacing the copy you hadn't started." : '.'));
      await loadSets(name, my);   // list the sets and open the imported one
    } catch (err) {
      app.importing = '';
      const msg = 'Not imported: ' + f.name + '. ' + err.message;
      app.dropErr = msg; showFlash(msg, true);   // always, on Home too; the screen stays as it was
      // the import bumped `nav`, which stopped a first load that was still opening a set: pick it up again
      if (my === app.nav && !app.view) (app.cur ? openSet(app.cur) : loadSets()).catch(() => {});
    }
  }
</script>

<svelte:window ondragenter={onDragEnter} ondragover={onDragOver} ondragleave={onDragLeave} ondrop={onDrop}
  onkeydown={e => { if (e.key === 'Escape' && askDrop) askDrop = null; }} />

<div id="drop-confirm" class="health" class:hidden={!askDrop} role="alertdialog" aria-label="Leave the round?">
  <span class="confirm-inline"><span>Open {askDrop?.name}? Your round keeps running while you're away. You can come back to it from the picker.</span>
    <button id="drop-confirm-open" class="btn btn-solid" type="button" onclick={dropOpen}>Open {askDrop?.name}</button><button id="drop-confirm-stay" bind:this={stayEl} class="btn btn-ghost" type="button" onclick={() => (askDrop = null)}>Stay in the round</button></span>
</div>

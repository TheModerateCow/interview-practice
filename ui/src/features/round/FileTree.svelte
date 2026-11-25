<script>
  import { showFlash } from '../../app.svelte.js';
  import { round, openFile, addFile } from './round.svelte.js';

  let newfile = $state('');
  const pick = f => openFile(f).catch(e => showFlash(e.message, true));
  async function onAdd(e) {
    e.preventDefault();
    try { await addFile(newfile, () => (newfile = '')); }
    catch (err) { showFlash(err.message, true); }
  }
</script>

<aside id="files" aria-label="Files">
  <div id="file-tree" role="tree" aria-label="Files">
    {#each round.st?.files || [] as f}
      <div role="treeitem" tabindex="0" title={f} data-testid={'file-' + f} class:sel={f === round.curFile} aria-selected={f === round.curFile ? 'true' : undefined}
        onclick={() => pick(f)} onkeydown={e => { if (e.key === 'Enter') pick(f); }}>{f}</div>
    {/each}
  </div>
  <form id="newfile-form" onsubmit={onAdd}><input id="newfile" bind:value={newfile} placeholder="+ New file" aria-label="New file path" autocomplete="off"></form>
</aside>

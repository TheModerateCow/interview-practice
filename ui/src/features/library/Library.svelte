<script>
  // The preset Library on Home: ready-made sets shipped with the app. Taking one opens a fresh copy's ready screen.
  import { onMount } from 'svelte';
  import { api } from '../../lib/api.js';
  import { ROUND, LANGNAME, cap } from '../../lib/util.js';
  import { showFlash } from '../../app.svelte.js';
  let { ontake } = $props();   // ontake(name): list the sets and open that one

  let presets = $state([]), taking = $state('');
  onMount(async () => { try { presets = (await api('/library')).presets; } catch (e) {} });

  async function take(p) {
    if (taking) return;
    taking = p.name;
    try { await ontake((await api('/library/' + encodeURIComponent(p.name), { method: 'POST' })).name); }
    catch (e) { showFlash(e.message, true); }
    finally { taking = ''; }
  }
</script>

{#if presets.length}
  <details id="library" class="sets" open>
    <summary class="label">Library · {presets.length}</summary>
    {#each presets as p (p.name)}
      <div class="set-item">
        <button type="button" class="set-row" data-preset={p.name} disabled={!!taking} onclick={() => take(p)}>
          <span class="set-title">{p.title}</span>
          <span class="set-meta">{[ROUND[p.round] || p.round, LANGNAME[p.language] || p.language, cap(p.difficulty), p.minutes + ' min'].join(' · ')}</span>
          <span class="set-name">{taking === p.name ? 'Opening…' : p.company || ''}</span>
        </button>
      </div>
    {/each}
  </details>
{/if}

<script>
  // The results dialog at the close: final grades, the event log, Export.
  import GradeRow from '../../components/GradeRow.svelte';
  import { showFlash } from '../../app.svelte.js';
  import { round, closedAt, closeFinal, doExport } from './round.svelte.js';
  const st = $derived(round.st);
</script>

<svelte:window onkeydown={e => { if (e.key === 'Escape' && round.finalOpen) closeFinal(); }} />

<div id="final" class:hidden={!round.finalOpen} role="dialog" aria-modal="true" aria-label="Results">
  {#if round.finalOpen && st}
    {@const g = st.final || {}}
    <div class="final-card">
      <div><div class="label">{st.title}</div><h2>{st.expired ? "Time's up" : 'Interview ended'}</h2></div>
      <div class="grades">
        {#each Object.entries(g) as [k, row]}<GradeRow tag={k} g={row} names={true} />{:else}<p class="muted">{!st.has_submit ? 'This set has no hidden tests (Run only).' : 'No final grade: ' + (st.final_error || 'press End to retry') + '.'}</p>{/each}
      </div>
      <p class="muted">Closed at {closedAt()} of {st.minutes} min. Export, then send export.zip to Claude for the debrief.</p>
      <div><div class="label">Where the time went</div><div class="events">
        {#each st.events || [] as e}
          {@const [before, ...after] = String(e[1]).split('(after time)')}
          <div><span>{e[0]}</span><span>{before}{#if after.length}<em>(after time)</em>{after.join('(after time)')}{/if}</span></div>
        {/each}
      </div></div>
      <div class="actions"><button id="final-export" class="btn btn-solid" type="button" aria-label="Export" onclick={() => doExport().catch(e => showFlash(e.message, true))}>Export</button>
        <button id="final-close" class="btn btn-ghost" type="button" onclick={closeFinal}>Close</button></div>
    </div>
  {/if}
</div>

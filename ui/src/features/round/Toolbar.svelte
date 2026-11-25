<script>
  import { tick as flush } from 'svelte';
  import { round, closedAt, openFinal, guarded, doRun, doMyTests, doSubmit, doExport, nextPart, endRound } from './round.svelte.js';

  let nextNoEl, endNoEl;
  const st = $derived(round.st);
  const busy = $derived(round.busy);
  const closedOn = $derived(!!st?.ended && !round.finalOpen);
  async function askNextPart() { round.askNext = true; await flush(); nextNoEl.focus(); }
  async function askEndRound() { round.askEnd = true; await flush(); endNoEl.focus(); }
</script>

<div class="toolbar">
  <button id="run-btn" class="btn btn-outline" type="button" aria-label="Run (Ctrl+')" disabled={!!busy} onclick={doRun}>Run <kbd>Ctrl '</kbd></button>
  <button id="mytests-btn" class="btn btn-outline" class:hidden={!st?.has_mytests} type="button" aria-label="Run my tests" disabled={!!busy} onclick={doMyTests}>My tests</button>
  <button id="submit-btn" class="btn btn-accent" class:hidden={!st?.has_submit} type="button" aria-label="Submit (Ctrl+Enter)" disabled={!!busy} onclick={doSubmit}>Submit <kbd>Ctrl ↵</kbd></button>
  <button id="next-btn" class="btn btn-ghost" class:hidden={!st?.has_next || round.askNext} type="button" aria-label="Next part" disabled={!!busy} onclick={askNextPart}>Next part</button>
  <span id="next-bar" class="confirm-inline" class:hidden={!round.askNext}><span id="next-bar-text">Show the next part now? This is logged as asked to move on.{st?.ended ? ' It is marked after time.' : ''}</span>
    <button id="next-yes" class="btn btn-solid" type="button" onclick={nextPart}>Show it</button><button id="next-no" bind:this={nextNoEl} class="btn btn-ghost" type="button" onclick={() => (round.askNext = false)}>Cancel</button></span>
  <button id="end-btn" class="btn btn-danger" class:hidden={round.askEnd} type="button" aria-label="End interview" disabled={!!busy} onclick={askEndRound}>End</button>
  <span id="end-bar" class="confirm-inline danger" class:hidden={!round.askEnd}>End now? Hidden tests run one last time and the clock stops.
    <button id="end-confirm" class="btn btn-danger strong" type="button" onclick={endRound}>End interview</button><button id="end-no" bind:this={endNoEl} class="btn btn-ghost" type="button" onclick={() => (round.askEnd = false)}>Keep going</button></span>
  <span class="spacer"></span>
  <span id="busy" class="busy" aria-live="polite">{#if busy && round.results?.kind !== 'loading'}<span class="loading">{busy}…</span>{/if}</span>
  <span id="save-status" class="saved">{round.saveStatus}</span>
  <button id="export-btn" class="btn btn-ghost" type="button" aria-label="Export" disabled={!!busy} onclick={() => guarded('Exporting', doExport)}>Export</button>
</div>
<div id="closed-bar" class="closed-bar" class:hidden={!closedOn} role="status"><span id="closed-text">{closedOn ? 'Round closed at ' + closedAt() + '. Anything you run, test or submit now is marked after time.' : ''}</span>
  <button id="closed-results" class="btn btn-ghost" type="button" onclick={openFinal}>Show results</button></div>

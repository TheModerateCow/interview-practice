<script>
  // The round screen: toolbar, then files | editor + stdin/results | problem, with resizable panes.
  import { onMount } from 'svelte';
  import { app } from '../../app.svelte.js';
  import { LS } from '../../lib/util.js';
  import { PANE_DEF, paneLimits, clampSize, parsePanes, splitter } from '../../lib/panes.js';
  import { round, setEditorEl, isDirty, save, doRun, doSubmit } from './round.svelte.js';
  import Toolbar from './Toolbar.svelte';
  import FileTree from './FileTree.svelte';
  import Results from './Results.svelte';
  import ProblemPane from './ProblemPane.svelte';
  import FinalDialog from './FinalDialog.svelte';

  let editorEl;
  onMount(() => setEditorEl(editorEl));   // always mounted: Monaco is created once, in this element

  function onKey(e) {
    if (!(e.ctrlKey || e.metaKey) || !round.st || app.view !== 'round') return;
    if (e.key === "'") { e.preventDefault(); doRun(); }
    else if (e.key === 'Enter') { e.preventDefault(); doSubmit(); }
  }

  // Pane sizes (drag or arrow keys), remembered in the browser. Stored raw; clamped live so a small window doesn't lose them.
  let panes = $state(parsePanes(LS.get('ilab.panes')));
  let winW = $state(window.innerWidth), edH = $state(0);
  const paneCtx = (files, problem) => ({ w: winW, h: edH, files, problem });
  const eff = $derived.by(() => {
    const files = clampSize('files', panes.files, paneCtx(panes.files, panes.problem));
    const problem = clampSize('problem', panes.problem, paneCtx(files, panes.problem));
    return { files, problem, bottom: panes.bottom == null || !edH ? panes.bottom : clampSize('bottom', panes.bottom, paneCtx(files, problem)) };
  });
  const bottomPx = $derived(Math.round(eff.bottom ?? 0.36 * edH));
  const lim = key => paneLimits(key, paneCtx(eff.files, eff.problem)).map(Math.round);
  const pane = (key, axis, sign) => ({
    axis, sign,
    cur: () => (key === 'bottom' ? bottomPx : eff[key]),
    set: px => { if (key !== 'bottom' || edH) panes[key] = clampSize(key, px, paneCtx(eff.files, eff.problem)); },
    reset: () => { panes[key] = PANE_DEF[key]; },
    done: () => LS.set('ilab.panes', JSON.stringify(panes)),
  });
</script>

<svelte:window bind:innerWidth={winW} onkeydown={onKey} onbeforeunload={() => { if (isDirty()) save(); }} />

<main id="round" class:hidden={app.view !== 'round'} style:--files-w="{eff.files}px" style:--problem-w="{eff.problem}px" style:--bottom-h={eff.bottom == null ? null : eff.bottom + 'px'}>
  <Toolbar />
  <div id="panes">
    <FileTree />
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (a focusable separator is the ARIA window splitter) -->
    <div id="split-files" class="splitter splitter-v" role="separator" aria-orientation="vertical" aria-label="Resize Files" tabindex="0"
      aria-valuenow={eff.files} aria-valuemin={lim('files')[0]} aria-valuemax={lim('files')[1]} use:splitter={pane('files', 'x', 1)}></div>
    <section id="editor-wrap" bind:clientHeight={edH}>
      <div class="editor-box">
        {#if !round.edReady}<div class="loading block cover" role="status">Loading the editor…</div>{/if}
        <div id="editor" bind:this={editorEl}></div>
      </div>
      <!-- svelte-ignore a11y_no_noninteractive_tabindex (a focusable separator is the ARIA window splitter) -->
      <div id="split-bottom" class="splitter splitter-h" role="separator" aria-orientation="horizontal" aria-label="Resize stdin and results" tabindex="0"
        aria-valuenow={bottomPx} aria-valuemin={lim('bottom')[0]} aria-valuemax={lim('bottom')[1]} use:splitter={pane('bottom', 'y', -1)}></div>
      <div id="bottom" class:solo={round.st?.has_examples}>
        {#if !round.st?.has_examples}<div class="stdin-wrap"><label for="stdin" class="label">stdin</label><textarea id="stdin" bind:value={round.stdin} spellcheck="false" placeholder="Input for Run"></textarea></div>{/if}
        <Results />
      </div>
    </section>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (a focusable separator is the ARIA window splitter) -->
    <div id="split-problem" class="splitter splitter-v" role="separator" aria-orientation="vertical" aria-label="Resize Problem" tabindex="0"
      aria-valuenow={eff.problem} aria-valuemin={lim('problem')[0]} aria-valuemax={lim('problem')[1]} use:splitter={pane('problem', 'x', -1)}></div>
    <ProblemPane />
  </div>
</main>

<FinalDialog />

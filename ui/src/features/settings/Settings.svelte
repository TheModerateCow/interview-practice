<script>
  // Settings: a panel over the current screen (not a screen, so a round keeps its clock). Word wrap and Theme.
  import ThemeToggle from '../../components/ThemeToggle.svelte';
  import { LS } from '../../lib/util.js';
  import { setWrap, setAssist } from '../../lib/monaco.js';
  import { applyLevel } from '../../lib/assist.js';
  import { app } from '../../app.svelte.js';
  import { round } from '../round/round.svelte.js';
  let wrap = $state(LS.get('ilab-wrap') === 'on'), panel = $state();
  const close = () => { app.settings = false; document.getElementById('settings-btn')?.focus(); };
  $effect(() => { if (round.finalOpen) app.settings = false; });            // 00:00 while open: the end card wins
  $effect(() => { if (app.settings) panel?.querySelector('button')?.focus(); });
</script>

<svelte:window onkeydown={e => { if (e.key === 'Escape' && app.settings) close(); }} />
<div id="settings" class="overlay settings" class:hidden={!app.settings} role="dialog" aria-labelledby="settings-title">
  <div class="final-card" bind:this={panel}>
    <h2 id="settings-title">Settings</h2>
    <div class="setting"><div><span id="wrap-label">Word wrap</span>
        <p>Long lines wrap at the editor's edge instead of scrolling sideways. Your code doesn't change.</p></div>
      <div id="wrap-pick" class="seg" role="group" aria-labelledby="wrap-label">
        {#each [[false, 'Off'], [true, 'On']] as [v, label]}
          <button type="button" data-wrap={v ? 'on' : 'off'} aria-pressed={String(wrap === v)} onclick={() => { wrap = v; setWrap(v); }}>{label}</button>
        {/each}</div></div>
    <div class="setting"><div><span id="assist-label">Code help</span>
        <p>Suggestions, parameter hints and error underlines. Real interviews differ: some have all of it, some none.</p></div>
      <div id="assist-pick" class="seg" role="group" aria-labelledby="assist-label">
        {#each [['full', 'Full'], ['words', 'Words only'], ['off', 'Off']] as [v, label]}
          <button type="button" data-assist={v} aria-pressed={String(app.assist === v)} onclick={() => { app.assist = v; setAssist(v); applyLevel(); }}>{label}</button>
        {/each}</div></div>
    <div class="setting"><div><span>Theme</span></div><ThemeToggle /></div>
    <p class="muted">The language problems open in is set on Home, above the problem list ("Practise in").</p>
    <div class="actions"><button id="settings-close" class="btn btn-outline" type="button" onclick={close}>Done</button></div>
  </div>
</div>

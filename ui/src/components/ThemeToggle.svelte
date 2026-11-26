<script>
  // Auto (system) / Light / Dark, remembered in the browser and shared with Monaco.
  import { onMount, flushSync } from 'svelte';
  import { LS } from '../lib/util.js';
  import { darkMQ, monacoTheme } from '../lib/monaco.js';

  const THEMES = [['', 'Auto', 'Follow system'], ['light', 'Light'], ['dark', 'Dark']];
  let theme = $state(LS.get('ilab-theme') || '');
  $effect(() => {
    if (theme) document.documentElement.dataset.theme = theme; else delete document.documentElement.dataset.theme;
    LS.set('ilab-theme', theme);
    monacoTheme();
  });
  onMount(() => darkMQ.addEventListener('change', () => { if (!theme) monacoTheme(); }));
  // Crossfade light <-> dark: the view transition snapshots the page (Monaco included) before and after.
  // flushSync runs the effect inside the callback so the new theme is on screen when the "after" snapshot is taken.
  function pick(t) {
    if (t === theme) return;
    const go = () => flushSync(() => (theme = t));
    document.startViewTransition ? document.startViewTransition(go) : go();
  }
</script>

<div class="seg" role="group" aria-label="Theme">
  {#each THEMES as [t, label, title]}<button type="button" data-t={t} aria-pressed={String(theme === t)} {title} onclick={() => pick(t)}>{label}</button>{/each}
</div>

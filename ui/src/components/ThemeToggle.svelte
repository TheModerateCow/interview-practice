<script>
  // Auto (system) / Light / Dark, remembered in the browser and shared with Monaco.
  import { onMount } from 'svelte';
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
</script>

<div class="seg" role="group" aria-label="Theme">
  {#each THEMES as [t, label, title]}<button type="button" data-t={t} aria-pressed={String(theme === t)} {title} onclick={() => (theme = t)}>{label}</button>{/each}
</div>

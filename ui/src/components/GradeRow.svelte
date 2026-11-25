<script>
  // One graded tag: count + meter, or the status when it couldn't be graded. Used by Results and the final dialog.
  let { tag, g, names } = $props();
  const pct = $derived(g.total ? Math.round(100 * g.passed / g.total) : 0);
</script>

<div class="grade"><span class="tag">{tag}</span>
  {#if g.status === 'graded'}
    <span class="count">{g.passed}/{g.total}</span><span class="meter" class:full={pct === 100}><i style:width="{pct}%"></i></span>
  {:else}
    <span class="count warn">—</span><span class="status">{g.status}{g.limit_s ? ' in ' + g.limit_s + ' s' : ''}</span>
  {/if}
  {#if (g.last_error || g.last_line) && (g.status !== 'graded' || g.passed < g.total)}<span class="why">{g.last_error || g.last_line}</span>{/if}
  {#if g.after_time}<span class="late">after time</span>{/if}
  {#if names && g.failed && g.failed.length}<span class="names">{g.failed.join('\n')}</span>{/if}
</div>

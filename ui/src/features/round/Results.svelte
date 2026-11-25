<script>
  // The results pane under the editor: Run output and testcases, or a grade list.
  import GradeRow from '../../components/GradeRow.svelte';
  import { vclass } from '../../lib/util.js';
  import { round } from './round.svelte.js';
  const results = $derived(round.results);
</script>

{#snippet caseOut(c)}
  {#if c.stdout}<pre class="out">{c.stdout}</pre>{/if}
  {#if c.stderr}<pre class="out bad">{c.stderr}</pre>{/if}
  {#if c.truncated}<p class="muted">Output truncated at 64 KB.</p>{/if}
  {#if !c.stdout && !c.stderr}<p class="muted">No output.</p>{/if}
{/snippet}

<div id="results" aria-live="polite">
  {#if results?.kind === 'empty'}
    <p class="empty">Run your code with <kbd>Ctrl '</kbd> or submit with <kbd>Ctrl ↵</kbd>. Results show here.</p>
  {:else if results?.kind === 'loading'}
    <div class="loading block" role="status">{results.msg}…</div>
  {:else if results?.kind === 'err'}
    <p class="err">{results.msg}</p>
  {:else if results?.kind === 'run'}
    {@const r = results.r}
    {@const c0 = r.stdin_case || (r.testcases || [])[0]}
    <div class="res-head"><span id="verdict" data-testid="verdict" class="badge {vclass(r.verdict)}">{r.verdict}</span>
      {#if results.late}<span class="late">after time</span>{/if}
      {#if c0}<span class="meta">{c0.ms} ms{r.memory_kb != null ? ' · ' + (r.memory_kb / 1024).toFixed(1) + ' MB' : ''}{r.stdin_case && r.stdin_case.exit != null ? ' · exit ' + r.stdin_case.exit : ''}</span>{/if}
    </div>
    {#if r.compile && !r.compile.ok}<pre class="out bad">{r.compile.log}</pre>{/if}
    {#if r.stdin_case}
      <div class="label" id="stdout-label">stdout{results.stdin ? '' : ' · empty stdin'}{#if r.stdin_case.verdict && r.stdin_case.verdict !== 'Accepted'} · <span class={vclass(r.stdin_case.verdict)}>{r.stdin_case.verdict}{r.stdin_case.exit != null ? ' (exit ' + r.stdin_case.exit + ')' : ''}</span>{/if}</div>
      <div id="stdout">{@render caseOut(r.stdin_case)}</div>
    {/if}
    {#if r.testcases && r.testcases.length}
      <div class="label">Testcases · {r.testcases.filter(c => c.pass).length}/{r.testcases.length} passed</div>
      <div class="tbl-wrap"><table><thead><tr><th></th><th>Input</th><th>Expected</th><th>Got</th></tr></thead><tbody>
        {#each r.testcases as c}<tr><td class={c.pass ? 'ok' : 'no'} aria-label={c.pass ? 'passed' : 'failed'}>{c.pass ? '✓' : '✗'}</td><td class="mono">{c.stdin}</td><td class="mono">{c.expected}</td><td class="mono">{c.stdout || c.stderr}{c.truncated ? ' (output truncated)' : ''}</td></tr>{/each}
      </tbody></table></div>
    {/if}
  {:else if results?.kind === 'grades'}
    <div class="label">{results.title}</div>
    <div class="grades">{#each Object.entries(results.rows) as [k, g]}<GradeRow tag={k} {g} names={results.names} />{:else}<p class="muted">No results.</p>{/each}</div>
  {/if}
</div>

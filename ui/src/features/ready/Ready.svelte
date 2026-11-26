<script>
  // The ready screen: what the round is, before the clock starts.
  import { ROUND, LANGNAME, cap, md } from '../../lib/util.js';
  import { assistLine } from '../../lib/assist.js';
  import { app } from '../../app.svelte.js';
  import { startRound } from '../../nav.js';
  const info = $derived(app.ready), err = $derived(app.readyErr);

  let starting = $state(false), startErr = $state('');
  $effect(() => { info; starting = false; startErr = ''; });   // each set opens with a fresh Start button
  async function start() {
    starting = true;
    try { await startRound(); }   // enters the round, or throws
    catch (e) { startErr = e.message; starting = false; }
  }
</script>

<main id="ready" class:hidden={app.view !== 'ready'}>
  {#if err}
    <div class="ready-card"><p class="err">{err}</p></div>
  {:else if info}
    {@const eyebrow = [info.company, info.role, ROUND[info.round] || info.round].filter(Boolean).join(' · ')}
    <div class="ready-card">
      {#if eyebrow}<div class="eyebrow">{eyebrow}</div>{/if}
      <h1>{info.title}</h1>
      <div id="ready-name" class="mono muted">{info.name}</div>
      <div class="pills"><span class="pill">{LANGNAME[info.language] || info.language}</span><span class="pill">{cap(info.difficulty)}</span><span class="pill mono">{info.minutes} min</span></div>
      {#if info.rules}<div class="rules md"><div class="label">Before you start</div>{@html md(info.rules)}</div>{/if}
      <p id="ready-assist" class="assist">{assistLine(info.language, app.assist)}</p>
      <div class="go"><button id="start-btn" class="btn btn-solid btn-lg" type="button" aria-label="Start interview" disabled={starting} onclick={start}>{#if starting}<span class="loading">Starting…</span>{:else}Start interview{/if}</button>
        <small>The clock starts when you press Start. The problem appears then.</small></div>
      <p id="start-err" class="err" role="alert">{startErr}</p>
    </div>
  {/if}
</main>

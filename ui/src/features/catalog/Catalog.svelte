<script>
  // The problem catalog on Home: built-in problems plus your own imports, filtered by round, language and difficulty.
  // Picking one opens its running attempt, an unstarted one, or a fresh copy, on the ready screen.
  import Dropdown from '../../components/Dropdown.svelte';
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, cap } from '../../lib/util.js';
  import { app, showFlash } from '../../app.svelte.js';
  let { onpick } = $props();   // onpick(attempt name): list the sets and open that one

  let problems = $state([]), picking = $state('');
  let f = $state(Object.assign({ round: '', language: '', difficulty: '' }, JSON.parse(LS.get('ilab.filters') || '{}')));
  $effect(() => LS.set('ilab.filters', JSON.stringify(f)));

  const load = async () => { try { problems = (await api('/catalog')).problems; } catch (e) {} };
  $effect(() => { if (app.view === 'home') load(); });   // on Home, and again after each round: attempt counts change

  const opts = (key, names, label) => [{ value: '', label: 'All ' + label }].concat(
    [...new Set(problems.map(p => p[key]))].sort().map(v => ({ value: v, label: names ? names[v] || v : cap(v) })));
  const shown = $derived(problems.filter(p => ['round', 'language', 'difficulty'].every(k => !f[k] || p[k] === f[k])));
  const LAST = { running: 'in progress', ended: 'finished' };
  const meta = p => [ROUND[p.round] || p.round, LANGNAME[p.language] || p.language, cap(p.difficulty), p.minutes + ' min'].join(' · ');
  const history = p => p.attempts ? `${p.attempts} attempt${p.attempts > 1 ? 's' : ''} · last ${LAST[p.last] || p.last}` : 'not tried';

  async function pick(p) {
    if (picking) return;
    picking = p.id;
    try { await onpick((await api('/catalog/' + encodeURIComponent(p.id) + '/attempt', { method: 'POST' })).name); }
    catch (e) { showFlash(e.message, true); }
    finally { picking = ''; }
  }
</script>

<section id="catalog" aria-label="Problems">
  <div class="catalog-head">
    <h2 class="label">Problems · {shown.length}{shown.length !== problems.length ? ' of ' + problems.length : ''}</h2>
    <div class="filters">
      <Dropdown id="f-round" label="Round" value={f.round} onchange={v => (f.round = v)} options={opts('round', ROUND, 'rounds')} />
      <Dropdown id="f-language" label="Language" value={f.language} onchange={v => (f.language = v)} options={opts('language', LANGNAME, 'languages')} />
      <Dropdown id="f-difficulty" label="Difficulty" value={f.difficulty} onchange={v => (f.difficulty = v)} options={opts('difficulty', null, 'levels')} />
    </div>
  </div>
  {#each shown as p (p.id)}
    <div class="set-item">
      <button type="button" class="set-row" data-problem={p.id} disabled={!!picking} onclick={() => pick(p)}>
        <span class="set-title">{p.title}{#if p.source === 'custom'} <span class="pill">Yours</span>{/if}</span>
        <span class="set-meta">{meta(p)}</span>
        <span class="set-name">{picking === p.id ? 'Opening…' : history(p)}</span>
      </button>
    </div>
  {:else}
    <p class="muted">{problems.length ? 'No problem matches these filters.' : 'No problems yet. Drop a set .zip from Claude to add one.'}</p>
  {/each}
</section>

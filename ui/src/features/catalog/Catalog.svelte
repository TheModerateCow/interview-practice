<script>
  // The problem catalog on Home: built-in problems plus your own imports, filtered by round and difficulty.
  // Each problem comes in one or more languages. "Practise in" (the switch) is the one language every row opens;
  // picking a row opens its running attempt in that language, an unstarted one, or a fresh copy, on the ready screen.
  import Dropdown from '../../components/Dropdown.svelte';
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, cap } from '../../lib/util.js';
  import { app, showFlash } from '../../app.svelte.js';
  let { onpick } = $props();   // onpick(attempt name): list the sets and open that one

  let problems = $state([]), picking = $state('');
  let lang = $state(LS.get('ilab.lang') || 'python');   // "Practise in": only the switch changes it
  let f = $state(Object.assign({ round: '', difficulty: '' }, JSON.parse(LS.get('ilab.filters') || '{}')));
  $effect(() => LS.set('ilab.filters', JSON.stringify(f)));

  const load = async () => { try { problems = (await api('/catalog')).problems; } catch (e) {} };
  $effect(() => { if (app.view === 'home') load(); });   // on Home, and again after each round: attempt counts change

  const langs = $derived([...new Set(problems.flatMap(p => p.languages))].sort());
  const chosen = $derived(langs.includes(lang) ? lang : langs[0]);
  const choose = l => { lang = l; LS.set('ilab.lang', l); };
  const opts = (key, names, label) => [{ value: '', label: 'All ' + label }].concat(
    [...new Set(problems.map(p => p[key]))].sort().map(v => ({ value: v, label: names ? names[v] || v : cap(v) })));
  const shown = $derived(problems.filter(p => (!f.round || p.round === f.round) && (!f.difficulty || p.difficulty === f.difficulty)));
  // the row opens: the chosen language, else the one you used last on this problem, else its first
  const langFor = p => [chosen, p.last_language].find(l => l && p.languages.includes(l)) || p.languages[0];
  const langWords = p => { const l = langFor(p), n = LANGNAME[l] || l; return p.languages.length === 1 && l !== chosen ? n + ' only' : n; };
  const LAST = { running: 'in progress', ended: 'finished' };
  const meta = p => [ROUND[p.round] || p.round, langWords(p), cap(p.difficulty), p.minutes + ' min'].join(' · ');
  const history = p => p.attempts ? `${p.attempts} attempt${p.attempts > 1 ? 's' : ''} · last ${LAST[p.last] || p.last}` : 'not tried';

  async function pick(p) {
    if (picking) return;
    const lang = langFor(p);
    picking = p.id;
    try {
      const r = await api('/catalog/' + encodeURIComponent(p.id) + '/attempt', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: lang }) });
      await onpick(r.name);
    }
    catch (e) { showFlash(e.message, true); }
    finally { picking = ''; }
  }
</script>

<section id="catalog" aria-label="Problems">
  <div class="catalog-head">
    <h2 class="label">Problems · {shown.length}{shown.length !== problems.length ? ' of ' + problems.length : ''}</h2>
    <div class="filters">
      {#if langs.length}
        <span class="lang-pick"><span id="lang-pick-label" class="label">Practise in</span>
          <span id="lang-pick" class="seg" role="group" aria-labelledby="lang-pick-label">
            {#each langs as l}<button type="button" data-lang={l} aria-pressed={String(l === chosen)} onclick={() => choose(l)}>{LANGNAME[l] || l}</button>{/each}
          </span></span>
      {/if}
      <Dropdown id="f-round" label="Round" value={f.round} onchange={v => (f.round = v)} options={opts('round', ROUND, 'rounds')} />
      <Dropdown id="f-difficulty" label="Difficulty" value={f.difficulty} onchange={v => (f.difficulty = v)} options={opts('difficulty', null, 'levels')} />
    </div>
  </div>
  {#each shown as p (p.id)}
    <button type="button" class="set-row" data-problem={p.id} disabled={!!picking} onclick={() => pick(p)}>
      <span class="set-title">{p.title}{#if p.source === 'custom'} <span class="pill">Yours</span>{/if}</span>
      <span class="set-meta">{meta(p)}</span>
      <span class="set-name">{picking === p.id ? 'Opening…' : history(p)}</span>
    </button>
  {:else}
    <p class="muted">{problems.length ? 'No problem matches these filters.' : 'No problems yet. Drop a set .zip from Claude to add one.'}</p>
  {/each}
</section>

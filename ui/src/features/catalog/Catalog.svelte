<script>
  // The problem catalog on Home: built-in problems plus your own imports, filtered by round, language and difficulty.
  // Each problem comes in one or more languages. Picking one (the row: your usual language; a chip: that language)
  // opens its running attempt in that language, an unstarted one, or a fresh copy, on the ready screen.
  import Dropdown from '../../components/Dropdown.svelte';
  import { api } from '../../lib/api.js';
  import { LS, ROUND, LANGNAME, cap } from '../../lib/util.js';
  import { app, showFlash } from '../../app.svelte.js';
  let { onpick } = $props();   // onpick(attempt name): list the sets and open that one

  let problems = $state([]), picking = $state('');
  let usual = $state(LS.get('ilab.lang') || '');   // the language last picked
  let f = $state(Object.assign({ round: '', language: '', difficulty: '' }, JSON.parse(LS.get('ilab.filters') || '{}')));
  $effect(() => LS.set('ilab.filters', JSON.stringify(f)));

  const load = async () => { try { problems = (await api('/catalog')).problems; } catch (e) {} };
  $effect(() => { if (app.view === 'home') load(); });   // on Home, and again after each round: attempt counts change

  const opts = (key, names, label) => [{ value: '', label: 'All ' + label }].concat(
    [...new Set(problems.flatMap(p => key === 'language' ? p.languages : [p[key]]))].sort().map(v => ({ value: v, label: names ? names[v] || v : cap(v) })));
  const shown = $derived(problems.filter(p => (!f.round || p.round === f.round) && (!f.difficulty || p.difficulty === f.difficulty)
    && (!f.language || p.languages.includes(f.language))));
  // the row opens: the filtered language, else your usual one, else the one you used last on this problem, else its first
  const langFor = p => [f.language, usual, p.last_language].find(l => l && p.languages.includes(l)) || p.languages[0];
  const LAST = { running: 'in progress', ended: 'finished' };
  const meta = p => [ROUND[p.round] || p.round, cap(p.difficulty), p.minutes + ' min'].join(' · ');
  const history = p => p.attempts ? `${p.attempts} attempt${p.attempts > 1 ? 's' : ''} · last ${LAST[p.last] || p.last}` : 'not tried';

  async function pick(p, lang = langFor(p)) {
    if (picking) return;
    picking = p.id; usual = lang; LS.set('ilab.lang', lang);
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
      <Dropdown id="f-round" label="Round" value={f.round} onchange={v => (f.round = v)} options={opts('round', ROUND, 'rounds')} />
      <Dropdown id="f-language" label="Language" value={f.language} onchange={v => (f.language = v)} options={opts('language', LANGNAME, 'languages')} />
      <Dropdown id="f-difficulty" label="Difficulty" value={f.difficulty} onchange={v => (f.difficulty = v)} options={opts('difficulty', null, 'levels')} />
    </div>
  </div>
  {#each shown as p (p.id)}
    <div class="set-item">
      <button type="button" class="set-row" data-problem={p.id} disabled={!!picking} onclick={() => pick(p)}
        aria-label="{p.title} in {LANGNAME[langFor(p)] || langFor(p)}">
        <span class="set-title">{p.title}{#if p.source === 'custom'} <span class="pill">Yours</span>{/if}</span>
        <span class="set-meta">{meta(p)}</span>
        <span class="set-name">{picking === p.id ? 'Opening…' : history(p)}</span>
      </button>
      <div class="langs" role="group" aria-label="Languages for {p.title}">
        {#each p.languages as l}
          <button type="button" class="lang-chip" class:usual={l === langFor(p)} data-lang={l} disabled={!!picking}
            aria-label="{p.title} in {LANGNAME[l] || l}" onclick={() => pick(p, l)}>{LANGNAME[l] || l}</button>
        {/each}
      </div>
    </div>
  {:else}
    <p class="muted">{problems.length ? 'No problem matches these filters.' : 'No problems yet. Drop a set .zip from Claude to add one.'}</p>
  {/each}
</section>

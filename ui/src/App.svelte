<script>
  import { onMount, tick as flush } from 'svelte';
  import Dropdown from './Dropdown.svelte';
  import { api, enc, LS, esc, md, ROUND, LANGNAME, cap, partName, mmss, statusWords, vclass, langOf, darkMQ, monacoTheme, loadMonaco } from './lib.js';

  const THEMES = [['', 'Auto', 'Follow system'], ['light', 'Light'], ['dark', 'Dark']];
  const UNLOCKED = 'New part unlocked. The problem pane has it.';
  const GROUPS = [['running', 'In progress'], ['ready', 'Not started'], ['ended', 'Finished']];

  // ---------- state shown on the page
  let view = $state('');            // '' (loading) | 'home' | 'ready' | 'round'
  let sets = $state([]);            // the picker
  let cur = $state(null);           // current set name
  let info = $state(null);          // ready screen
  let readyErr = $state('');
  let st = $state(null);            // round state from the server
  let deadline = $state(0), now = $state(Date.now());
  let curFile = $state(null);
  let results = $state(null);       // results pane: null | {kind: 'empty' | 'err' | 'run' | 'grades', ...}
  let finalOpen = $state(false);
  let busy = $state('');            // label of the running action; '' when idle
  let loading = $state('Loading sets');   // page-level wait while no screen is shown
  let importing = $state('');       // file name of a zip being imported
  let edReady = $state(false);      // Monaco has loaded
  let saveStatus = $state('');
  let askNext = $state(false), askEnd = $state(false), askDrop = $state(null);
  let starting = $state(false), startErr = $state('');
  let dropErr = $state(''), healthMsg = $state('');
  let flash = $state({ text: '', bad: false, on: false, n: 0 });
  let theme = $state(LS.get('ilab-theme') || '');
  let over = $state(false);         // a file is being dragged over the page
  let stdin = $state(''), newfile = $state('');
  let editorEl, nextNoEl, endNoEl, dropStayEl;

  // ---------- plain variables: not shown, or Monaco objects that must not be wrapped in $state
  let ed = null, models = {}, dirty = false, saveT, pollT, tickT, flashT, dragN = 0;
  let closing = false, closeTry = 0, closeErr = false;

  // ---------- derived
  const left = $derived(!st ? 0 : st.ended ? Math.ceil(st.left_s) : Math.max(0, Math.ceil((deadline - now) / 1000)));
  const closedAt = () => mmss(Math.max(0, st.minutes * 60 - st.left_s));
  const closedOn = $derived(!!st?.ended && !finalOpen);
  const done = t => { const g = (st?.results || {})[t]; return g && g.status === 'graded' && g.total > 0 && g.passed === g.total; };
  const chips = $derived.by(() => {
    const tags = st?.unlocked || [];
    if (tags.length < 2 && !done(tags[0])) return [];
    const current = tags.find(t => !done(t));
    return tags.map(t => ({ label: (done(t) ? '✓ ' : '') + partName(t), cls: done(t) ? 'done' : t === current ? 'current' : '' }));
  });
  // One string: a poll that changes nothing leaves the pane (and its scroll position) alone.
  const problemHtml = $derived.by(() => {
    if (!st) return '';
    let h = md(st.problem);
    (st.parts || []).forEach(p => {
      const at = (st.events || []).find(e => String(e[1]).includes('revealed ' + p.file));
      h += '<div class="part-divider">New part' + (at ? ' · ' + esc(at[0]) + ' min' : '') + '</div>' + md(p.md);
    });
    return h;
  });

  // ---------- theme: Auto (system) / Light / Dark, shared with Monaco
  $effect(() => {
    if (theme) document.documentElement.dataset.theme = theme; else delete document.documentElement.dataset.theme;
    LS.set('ilab-theme', theme);
    monacoTheme();
  });
  $effect(() => { document.body.classList.toggle('over', over); });

  // ---------- files and Monaco
  const editor = () => loadMonaco(editorEl, {
    change: () => { dirty = true; saveStatus = 'Unsaved'; clearTimeout(saveT); saveT = setTimeout(save, 800); },
    run: () => doRun(),
    submit: () => doSubmit(),
  }).then(e => { ed = e; edReady = true; });

  async function openFile(p) {
    await save();
    const set = cur;
    const text = await (await api('/sets/' + set + '/files/' + enc(p), {}, true)).text();
    await editor();
    if (set !== cur) return;   // the user went elsewhere while this loaded
    const monaco = window.monaco;
    if (models[p]) models[p].dispose();
    models[p] = monaco.editor.createModel(text, langOf(p), monaco.Uri.parse('inmemory:///' + enc(p)));
    curFile = p; dirty = false;
    ed.setModel(models[p]);
    saveStatus = 'Saved';
  }
  const pick = f => openFile(f).catch(e => showFlash(e.message, true));

  async function save() {
    clearTimeout(saveT);
    if (!dirty || !curFile || !models[curFile]) return;
    dirty = false;
    try {
      await api('/sets/' + cur + '/files/' + enc(curFile), { method: 'PUT', body: models[curFile].getValue() });
      saveStatus = 'Saved';
    } catch (e) { dirty = true; saveStatus = 'Save failed: ' + e.message; }
  }

  async function addFile(e) {
    e.preventDefault();
    const p = newfile.trim().replace(/^\/+/, ''); if (!p) return;
    try {
      await api('/sets/' + cur + '/files/' + enc(p), { method: 'PUT', body: '' });
      newfile = '';
      if (!st.files.includes(p)) st.files.push(p);
      await openFile(p);
    } catch (err) { showFlash(err.message, true); }
  }

  // ---------- screens
  function screen(v) {
    view = v;
    if (v !== 'round') { clearInterval(pollT); clearInterval(tickT); }
  }

  // Every navigation bumps `nav`; an older async step that sees a newer value stops, so the latest one wins.
  let nav = 0;

  async function loadSets(select, my = nav) {   // first load, and after an import
    sets = (await api('/sets')).sets;
    if (my !== nav) return;
    if (select && sets.some(s => s.name === select)) return openSet(select);   // just imported
    // A round in progress resumes (a reload mid-round lands back in it); otherwise start at home.
    const running = sets.filter(s => s.status === 'running').map(s => s.name);
    const resume = running.includes(LS.get('ilab-last')) ? LS.get('ilab-last') : running[0];
    if (resume) return openSet(resume);
    return goHome();
  }

  // Save, then drop everything that belongs to the current set.
  async function leaveSet() {
    await save();
    finalOpen = false; askNext = false; askEnd = false;
    Object.values(models).forEach(m => m.dispose()); models = {}; curFile = null; st = null;
    results = null; info = null; readyErr = '';
  }

  async function goHome() {
    const my = ++nav;
    await leaveSet(); if (my !== nav) return;
    cur = null; loading = ''; screen('home');
    try { const fresh = (await api('/sets')).sets; if (my === nav) sets = fresh; } catch (e) {}   // fresh statuses: rounds may have timed out
  }

  async function openSet(name, my = ++nav) {
    await leaveSet(); if (my !== nav) return;
    cur = name; LS.set('ilab-last', name);
    screen(''); loading = 'Opening ' + (sets.find(s => s.name === name)?.title || name);
    try {
      const i = await api('/sets/' + name); if (my !== nav) return;
      if (i.status === 'ready') { info = i; starting = false; startErr = ''; screen('ready'); return; }
      const s = await api('/sets/' + name + '/state'); if (my !== nav) return;
      await enterRound(s, my);
    } catch (e) { if (my === nav) { screen('ready'); readyErr = e.message; } }
    finally { if (my === nav) loading = ''; }
  }

  async function startRound() {
    starting = true;
    try { await enterRound(await api('/sets/' + cur + '/start', { method: 'POST' }), ++nav); }
    catch (e) { startErr = e.message; starting = false; }
  }

  async function enterRound(s, my) {
    screen('round'); st = null; results = { kind: 'empty' };
    setState(s);
    await flush();   // the round screen is visible before Monaco measures its box
    await editor(); if (my !== nav) return;
    const first = st.files.find(f => f === st.run_entry) || st.files[0];
    if (first) await openFile(first);
    if (my !== nav) return;
    clearInterval(pollT); clearInterval(tickT);
    pollT = setInterval(poll, 5000); tickT = setInterval(clockTick, 250); clockTick();
    if (st.ended) openFinal();
  }

  function setState(s) {
    st = s;
    deadline = Date.now() + s.left_s * 1000;   // server "now" cancels out: left_s is relative to it
    const o = sets.find(x => x.name === cur);
    if (o) { o.title = s.title; o.status = s.status; o.left_s = s.left_s; }
  }

  async function poll() {
    if (!cur) return;
    try {
      const s = await api('/sets/' + cur + '/state');
      if (s.name === cur || !s.name) { const wasEnded = st && st.ended; setState(s); if (s.ended && !wasEnded) openFinal(); }
    } catch (e) {}
  }

  function clockTick() {
    if (!st) return;
    now = Date.now();
    if (left === 0 && !st.ended) autoClose();
  }

  // 00:00 closes the round: save, then the same call as End. Retries on the next tick after 5 s if it fails.
  async function autoClose() {
    if (closing || busy || Date.now() - closeTry < 5000) return;
    closing = true; closeTry = Date.now(); const name = cur;
    busy = 'Time is up: running hidden tests one last time';
    try {
      await save();
      const s = await api('/sets/' + name + '/end', { method: 'POST' });
      if (name !== cur) return;
      closeErr = false; setState(s); openFinal();
    } catch (e) {
      if (name === cur && !closeErr) { closeErr = true; results = { kind: 'err', msg: 'Time is up but the round could not be closed: ' + e.message + ' Retrying.' }; }
    } finally { closing = false; busy = ''; }
  }

  const openFinal = () => { if (st) finalOpen = true; };
  const closeFinal = () => { finalOpen = false; };

  // ---------- actions
  function showFlash(text, bad) {
    flash = { text, bad: !!bad, on: true, n: flash.n + 1 };   // a new n re-creates the toast, so a repeat visibly re-shows
    clearTimeout(flashT); flashT = setTimeout(() => { flash.on = false; }, bad ? 10000 : 5000);
  }

  async function guarded(label, fn) {
    if (busy || !st) return;
    busy = label;
    try { await save(); await fn(); }
    catch (e) { results = { kind: 'err', msg: e.message }; }
    finally { busy = ''; }
  }

  function doRun() {
    guarded('Running', async () => {
      results = { kind: 'loading', msg: 'Running ' + (curFile || 'your code') };
      const r = await api('/sets/' + cur + '/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file: curFile, stdin }) });
      results = { kind: 'run', r, late: !!st.ended };
    });
  }

  function doMyTests() {
    guarded('Running your tests', async () => {
      results = { kind: 'loading', msg: 'Running your tests' };
      const g = await api('/sets/' + cur + '/mytests', { method: 'POST' });
      results = { kind: 'grades', title: 'My tests', rows: { 'my tests': g }, names: true };
    });
  }

  function doSubmit() {
    if (!st || !st.has_submit) return;
    guarded('Submitting', async () => {
      const was = st.ended;
      results = { kind: 'loading', msg: 'Running hidden tests' };
      const r = await api('/sets/' + cur + '/submit', { method: 'POST' });
      results = { kind: 'grades', title: 'Hidden tests', rows: r.results, names: false };
      setState(r.state);
      if ((r.revealed || []).length) showFlash(UNLOCKED);
      if (r.state.ended && !was) openFinal();
    });
  }

  async function doExport() {
    await save();
    const r = await api('/sets/' + cur + '/export', {}, true);
    const u = URL.createObjectURL(await r.blob());
    const a = document.createElement('a'); a.href = u; a.download = 'export.zip'; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 10000);
    showFlash('Downloaded export.zip. Send it to Claude for the debrief. A copy is in data/exports/.');
  }

  async function askNextPart() { askNext = true; await flush(); nextNoEl.focus(); }
  function nextPart() {
    askNext = false;
    guarded('Revealing the next part', async () => {
      const before = (st.parts || []).length;
      setState(await api('/sets/' + cur + '/next', { method: 'POST' }));
      if (st.parts.length > before) showFlash(UNLOCKED);
    });
  }

  async function askEndRound() { askEnd = true; await flush(); endNoEl.focus(); }
  function endRound() {
    askEnd = false;
    guarded('Ending: running hidden tests one last time', async () => { setState(await api('/sets/' + cur + '/end', { method: 'POST' })); openFinal(); });
  }

  function onKey(e) {
    if (e.key === 'Escape' && askDrop) { askDrop = null; return; }
    if (e.key === 'Escape' && finalOpen) { closeFinal(); return; }
    if (!(e.ctrlKey || e.metaKey) || !st || view !== 'round') return;
    if (e.key === "'") { e.preventDefault(); doRun(); }
    else if (e.key === 'Enter') { e.preventDefault(); doSubmit(); }
  }

  // ---------- drag & drop import: the only import path
  const hasFiles = e => e.dataTransfer && [...(e.dataTransfer.types || [])].includes('Files');
  function onDragEnter(e) { if (hasFiles(e)) { e.preventDefault(); dragN++; over = true; } }
  function onDragOver(e) { if (hasFiles(e)) e.preventDefault(); }
  function onDragLeave(e) { if (hasFiles(e) && --dragN <= 0) { dragN = 0; over = false; } }
  // A round in progress: the open (or still opening) set is started and not closed. Anything else needs no question.
  async function roundRunning() {
    if (view === 'round' && st) return !st.ended;
    if (view === 'ready' || view === 'home') return false;
    try {   // still opening: the page's first load may not know yet, so ask the server
      const running = (await api('/sets')).sets.filter(s => s.status === 'running').map(s => s.name);
      const last = LS.get('ilab-last');
      return running.includes(cur || (running.includes(last) ? last : running[0]));
    } catch (e) { return false; }
  }
  async function onDrop(e) {
    e.preventDefault(); dragN = 0; over = false;
    const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (!f) return;
    if (await roundRunning()) { askDrop = f; await flush(); dropStayEl.focus(); return; }
    return doImport(f);
  }
  const dropOpen = () => { const f = askDrop; askDrop = null; return doImport(f); };

  async function doImport(f) {
    dropErr = ''; importing = f.name;
    const my = ++nav;   // a first load still in flight never lands on top of the drop
    try {
      const { name, title, replaced } = await api('/import', { method: 'POST', body: await f.arrayBuffer() });
      importing = '';
      showFlash('Imported ' + title + ' (' + name + ')' + (replaced ? ", replacing the copy you hadn't started." : '.'));
      await loadSets(name, my);
    } catch (err) {
      importing = '';
      const msg = 'Not imported: ' + f.name + '. ' + err.message;
      dropErr = msg; showFlash(msg, true);   // always, on Home too; the screen stays as it was
      // the import bumped `nav`, which stopped a first load that was still opening a set: pick it up again
      if (my === nav && !view) (cur ? openSet(cur) : loadSets()).catch(() => {});
    }
  }

  async function checkHealth() {
    try {
      const h = await api('/health'); const m = [];
      if (!h.docker) m.push(h.error || 'Docker is unreachable. Start Docker, then reload this page.');
      Object.entries(h.images || {}).forEach(([k, v]) => {
        if (v === 'pulling') m.push('Preparing the ' + k + ' runner image…');
        else if (v === 'missing') m.push('The ' + k + ' runner image is missing. Run ./install.sh.');
      });
      healthMsg = m.join(' ');
    } catch (e) { healthMsg = e.message; }
  }

  onMount(() => {
    darkMQ.addEventListener('change', () => { if (!theme) monacoTheme(); });
    checkHealth(); setInterval(checkHealth, 15000);
    loadSets().catch(e => { screen('home'); dropErr = e.message; });
  });
</script>

<svelte:window onkeydown={onKey} ondragenter={onDragEnter} ondragover={onDragOver} ondragleave={onDragLeave} ondrop={onDrop}
  onbeforeunload={() => { if (dirty) save(); }} />

{#snippet gradeRow(tag, g, names)}
  <div class="grade"><span class="tag">{tag}</span>
    {#if g.status === 'graded'}
      {@const pct = g.total ? Math.round(100 * g.passed / g.total) : 0}
      <span class="count">{g.passed}/{g.total}</span><span class="meter" class:full={pct === 100}><i style:width="{pct}%"></i></span>
    {:else}
      <span class="count warn">—</span><span class="status">{g.status}{g.limit_s ? ' in ' + g.limit_s + ' s' : ''}</span>
    {/if}
    {#if (g.last_error || g.last_line) && (g.status !== 'graded' || g.passed < g.total)}<span class="why">{g.last_error || g.last_line}</span>{/if}
    {#if g.after_time}<span class="late">after time</span>{/if}
    {#if names && g.failed && g.failed.length}<span class="names">{g.failed.join('\n')}</span>{/if}
  </div>
{/snippet}

{#snippet caseOut(c)}
  {#if c.stdout}<pre class="out">{c.stdout}</pre>{/if}
  {#if c.stderr}<pre class="out bad">{c.stderr}</pre>{/if}
  {#if c.truncated}<p class="muted">Output truncated at 64 KB.</p>{/if}
  {#if !c.stdout && !c.stderr}<p class="muted">No output.</p>{/if}
{/snippet}

<header id="top">
  <strong class="brand">Interview Lab</strong>
  <button id="home-btn" class="btn btn-ghost" class:hidden={!view || view === 'home'} type="button" onclick={goHome}>All sets</button>
  {#if sets.length && view !== 'home'}
    <Dropdown id="set-picker" label="Interview set" value={cur} onchange={openSet}
      options={sets.map(s => ({ value: s.name, label: s.title, meta: s.name + ' · ' + statusWords(s) }))} />
  {/if}
  <span class="spacer"></span>
  <div id="parts" class="parts" class:hidden={view !== 'round'} aria-label="Parts">
    {#each chips as c}<span class="chip {c.cls}">{c.label}</span>{/each}
  </div>
  <div id="timer-wrap" class="timer-wrap" class:hidden={view !== 'round'}><span id="timer-label" class="label">{st?.ended ? 'closed' : 'left'}</span><span id="timer" class="timer"
    class:low={!!st && !st.ended && left > 0 && left <= 300} class:over={!!st && (!!st.expired || (!st.ended && left === 0))}
    role="timer" aria-label="Time left">{st ? mmss(left) : '--:--'}</span></div>
  <div class="seg" role="group" aria-label="Theme">
    {#each THEMES as [t, label, title]}<button type="button" data-t={t} aria-pressed={String(theme === t)} {title} onclick={() => (theme = t)}>{label}</button>{/each}
  </div>
</header>
<div id="drop-confirm" class="health" class:hidden={!askDrop} role="alertdialog" aria-label="Leave the round?">
  <span class="confirm-inline"><span>Open {askDrop?.name}? Your round keeps running while you're away. You can come back to it from the picker.</span>
    <button id="drop-confirm-open" class="btn btn-solid" type="button" onclick={dropOpen}>Open {askDrop?.name}</button><button id="drop-confirm-stay" bind:this={dropStayEl} class="btn btn-ghost" type="button" onclick={() => (askDrop = null)}>Stay in the round</button></span>
</div>
<div id="health" class="health" class:hidden={!healthMsg} role="alert">{healthMsg}</div>
{#if !view && loading}<div class="loading block" role="status">{loading}…</div>{/if}

<main id="dropzone" class:hidden={view !== 'home'} class:over>
  <div class="home">
    <div class="drop">
      <h1 class="drop-big">Drop a set .zip here</h1>
      <p>Sets come from Claude's interview-practice skill. Drag the .zip anywhere onto this page.</p>
      <p id="drop-error" class="err" role="alert">{dropErr}</p>
    </div>
    {#each GROUPS as [status, label]}
      {@const list = sets.filter(s => s.status === status)}
      {#if list.length}
        <details class="sets" open={status !== 'ended'}>
          <summary class="label">{label} · {list.length}</summary>
          {#each list as s (s.name)}
            <button type="button" class="set-row" onclick={() => openSet(s.name)}>
              <span class="set-title">{s.title}</span>
              <span class="set-meta">{[ROUND[s.round] || s.round, LANGNAME[s.language] || s.language, status === 'running' && statusWords(s)].filter(Boolean).join(' · ')}</span>
              <span class="set-name">{s.name}</span>
            </button>
          {/each}
        </details>
      {/if}
    {/each}
  </div>
</main>

<main id="ready" class:hidden={view !== 'ready'}>
  {#if readyErr}
    <div class="ready-card"><p class="err">{readyErr}</p></div>
  {:else if info}
    {@const eyebrow = [info.company, info.role, ROUND[info.round] || info.round].filter(Boolean).join(' · ')}
    <div class="ready-card">
      {#if eyebrow}<div class="eyebrow">{eyebrow}</div>{/if}
      <h1>{info.title}</h1>
      <div id="ready-name" class="mono muted">{info.name}</div>
      <div class="pills"><span class="pill">{LANGNAME[info.language] || info.language}</span><span class="pill">{cap(info.difficulty)}</span><span class="pill mono">{info.minutes} min</span></div>
      {#if info.rules}<div class="rules md"><div class="label">Before you start</div>{@html md(info.rules)}</div>{/if}
      <div class="go"><button id="start-btn" class="btn btn-solid btn-lg" type="button" aria-label="Start interview" disabled={starting} onclick={startRound}>{#if starting}<span class="loading">Starting…</span>{:else}Start interview{/if}</button>
        <small>The clock starts when you press Start. The problem appears then.</small></div>
      <p id="start-err" class="err" role="alert">{startErr}</p>
    </div>
  {/if}
</main>

<main id="round" class:hidden={view !== 'round'}>
  <div class="toolbar">
    <button id="run-btn" class="btn btn-outline" type="button" aria-label="Run (Ctrl+')" disabled={!!busy} onclick={doRun}>Run <kbd>Ctrl '</kbd></button>
    <button id="mytests-btn" class="btn btn-outline" class:hidden={!st?.has_mytests} type="button" aria-label="Run my tests" disabled={!!busy} onclick={doMyTests}>My tests</button>
    <button id="submit-btn" class="btn btn-accent" class:hidden={!st?.has_submit} type="button" aria-label="Submit (Ctrl+Enter)" disabled={!!busy} onclick={doSubmit}>Submit <kbd>Ctrl ↵</kbd></button>
    <button id="next-btn" class="btn btn-ghost" class:hidden={!st?.has_next || askNext} type="button" aria-label="Next part" disabled={!!busy} onclick={askNextPart}>Next part</button>
    <span id="next-bar" class="confirm-inline" class:hidden={!askNext}><span id="next-bar-text">Show the next part now? This is logged as asked to move on.{st?.ended ? ' It is marked after time.' : ''}</span>
      <button id="next-yes" class="btn btn-solid" type="button" onclick={nextPart}>Show it</button><button id="next-no" bind:this={nextNoEl} class="btn btn-ghost" type="button" onclick={() => (askNext = false)}>Cancel</button></span>
    <button id="end-btn" class="btn btn-danger" class:hidden={askEnd} type="button" aria-label="End interview" disabled={!!busy} onclick={askEndRound}>End</button>
    <span id="end-bar" class="confirm-inline danger" class:hidden={!askEnd}>End now? Hidden tests run one last time and the clock stops.
      <button id="end-confirm" class="btn btn-danger strong" type="button" onclick={endRound}>End interview</button><button id="end-no" bind:this={endNoEl} class="btn btn-ghost" type="button" onclick={() => (askEnd = false)}>Keep going</button></span>
    <span class="spacer"></span>
    <span id="busy" class="busy" aria-live="polite">{#if busy && results?.kind !== 'loading'}<span class="loading">{busy}…</span>{/if}</span>
    <span id="save-status" class="saved">{saveStatus}</span>
    <button id="export-btn" class="btn btn-ghost" type="button" aria-label="Export" disabled={!!busy} onclick={() => guarded('Exporting', doExport)}>Export</button>
  </div>
  <div id="closed-bar" class="closed-bar" class:hidden={!closedOn} role="status"><span id="closed-text">{closedOn ? 'Round closed at ' + closedAt() + '. Anything you run, test or submit now is marked after time.' : ''}</span>
    <button id="closed-results" class="btn btn-ghost" type="button" onclick={openFinal}>Show results</button></div>
  <div id="panes">
    <aside id="files" aria-label="Files">
      <div id="file-tree" role="tree" aria-label="Files">
        {#each st?.files || [] as f}
          <div role="treeitem" tabindex="0" title={f} data-testid={'file-' + f} class:sel={f === curFile} aria-selected={f === curFile ? 'true' : undefined}
            onclick={() => pick(f)} onkeydown={e => { if (e.key === 'Enter') pick(f); }}>{f}</div>
        {/each}
      </div>
      <form id="newfile-form" onsubmit={addFile}><input id="newfile" bind:value={newfile} placeholder="+ New file" aria-label="New file path" autocomplete="off"></form>
    </aside>
    <section id="editor-wrap">
      <div class="editor-box">
        {#if !edReady}<div class="loading block cover" role="status">Loading the editor…</div>{/if}
        <div id="editor" bind:this={editorEl}></div>
      </div>
      <div id="bottom">
        <div class="stdin-wrap"><label for="stdin" class="label">stdin</label><textarea id="stdin" bind:value={stdin} spellcheck="false" placeholder="Input for Run"></textarea></div>
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
            {#if r.stdin_case}{@render caseOut(r.stdin_case)}{/if}
            {#if r.testcases && r.testcases.length}
              <div class="tbl-wrap"><table><thead><tr><th></th><th>Input</th><th>Expected</th><th>Got</th></tr></thead><tbody>
                {#each r.testcases as c}<tr><td class={c.pass ? 'ok' : 'no'} aria-label={c.pass ? 'passed' : 'failed'}>{c.pass ? '✓' : '✗'}</td><td class="mono">{c.stdin}</td><td class="mono">{c.expected}</td><td class="mono">{c.stdout || c.stderr}{c.truncated ? ' (output truncated)' : ''}</td></tr>{/each}
              </tbody></table></div>
            {/if}
          {:else if results?.kind === 'grades'}
            <div class="label">{results.title}</div>
            <div class="grades">{#each Object.entries(results.rows) as [k, g]}{@render gradeRow(k, g, results.names)}{:else}<p class="muted">No results.</p>{/each}</div>
          {/if}
        </div>
      </div>
    </section>
    <section id="problem" class="md" aria-label="Problem">{@html problemHtml}</section>
  </div>
</main>

<div id="final" class:hidden={!finalOpen} role="dialog" aria-modal="true" aria-label="Results">
  {#if finalOpen && st}
    {@const g = st.final || {}}
    <div class="final-card">
      <div><div class="label">{st.title}</div><h2>{st.expired ? "Time's up" : 'Interview ended'}</h2></div>
      <div class="grades">
        {#each Object.entries(g) as [k, row]}{@render gradeRow(k, row, true)}{:else}<p class="muted">{!st.has_submit ? 'This set has no hidden tests (Run only).' : 'No final grade: ' + (st.final_error || 'press End to retry') + '.'}</p>{/each}
      </div>
      <p class="muted">Closed at {closedAt()} of {st.minutes} min. Export, then send export.zip to Claude for the debrief.</p>
      <div><div class="label">Where the time went</div><div class="events">
        {#each st.events || [] as e}
          {@const [before, ...after] = String(e[1]).split('(after time)')}
          <div><span>{e[0]}</span><span>{before}{#if after.length}<em>(after time)</em>{after.join('(after time)')}{/if}</span></div>
        {/each}
      </div></div>
      <div class="actions"><button id="final-export" class="btn btn-solid" type="button" aria-label="Export" onclick={() => doExport().catch(e => showFlash(e.message, true))}>Export</button>
        <button id="final-close" class="btn btn-ghost" type="button" onclick={closeFinal}>Close</button></div>
    </div>
  {/if}
</div>
{#if importing}<div class="toast" role="status"><span class="loading">Importing {importing}…</span></div>{/if}
{#key flash.n}<div id="flash" class="toast" class:hidden={!flash.on} class:bad={flash.bad} role="status">{flash.text}</div>{/key}

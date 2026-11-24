'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const md = s => (window.marked ? marked.parse(String(s || '')) : '<pre>' + esc(s) + '</pre>');
const show = (el, on) => $(el).classList.toggle('hidden', !on);
const LS = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
             set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };

async function api(path, opts = {}, raw) {
  opts.headers = Object.assign({ 'X-ILab': '1' }, opts.headers || {});
  let r;
  try { r = await fetch('/api' + path, opts); }
  catch (e) { throw new Error('Cannot reach the server: ' + e.message); }
  if (!r.ok) {
    let m = r.status + ' ' + r.statusText;
    try { m = (await r.json()).error || m; } catch (e) {}
    throw new Error(m);
  }
  return raw ? r : r.json();
}
const enc = p => p.split('/').map(encodeURIComponent).join('/');

let cur = null;        // current set name
let st = null;         // current state
let ed = null, monacoP = null, models = {}, curFile = null;
let deadline = 0, pollT = null, tickT = null, saveT = null, dirty = false, busy = false;
let partsSeen = 0;

/* ---------- theme: Auto (system) / Light / Dark, shared with Monaco ---------- */
const darkMQ = matchMedia('(prefers-color-scheme: dark)');
function isDark() { const t = document.documentElement.dataset.theme; return t ? t === 'dark' : darkMQ.matches; }
function setTheme(t) {
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  LS.set('ilab-theme', t || '');
  document.querySelectorAll('.seg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === (t || ''))));
  monacoTheme();
}
function monacoTheme() {
  if (!window.monaco) return;
  const cs = getComputedStyle(document.documentElement), v = n => cs.getPropertyValue(n).trim();
  const c = n => v(n).replace('#', '');   // token colours are hex: Monaco wants them without '#'
  monaco.editor.defineTheme('ilab', {
    base: isDark() ? 'vs-dark' : 'vs', inherit: true,
    rules: [
      { token: '', foreground: c('--fg') },
      { token: 'keyword', foreground: c('--code-keyword') },
      { token: 'string', foreground: c('--code-string') },
      { token: 'number', foreground: c('--code-number') },
      { token: 'comment', foreground: c('--code-comment'), fontStyle: 'italic' },
      { token: 'type', foreground: c('--code-type') },
      { token: 'type.identifier', foreground: c('--code-type') },
      { token: 'identifier', foreground: c('--code-function') },
    ],
    colors: {
      'editor.background': v('--code-bg'), 'editor.foreground': v('--fg'),
      'editorLineNumber.foreground': v('--fg-3'), 'editorLineNumber.activeForeground': v('--fg'),
      'editor.lineHighlightBackground': v('--code-line-hl'), 'editor.lineHighlightBorder': v('--code-line-hl'),
      'editor.selectionBackground': v('--code-selection'), 'editorCursor.foreground': v('--accent'),
      'editorIndentGuide.background1': v('--line'), 'editorWhitespace.foreground': v('--line-strong'),
      'editorWidget.background': v('--surface'), 'editorWidget.border': v('--line-strong'),
      'editorSuggestWidget.background': v('--surface'), 'editorSuggestWidget.selectedBackground': v('--surface-2'),
      'focusBorder': v('--focus'), 'scrollbarSlider.background': v('--line-strong'),
    },
  });
  monaco.editor.setTheme('ilab');
}
darkMQ.addEventListener('change', () => { if (!document.documentElement.dataset.theme) monacoTheme(); });

/* ---------- Monaco ---------- */
function loadMonaco() {
  if (monacoP) return monacoP;
  monacoP = new Promise((res, rej) => {
    const base = location.origin + '/vendor/monaco/vs';
    self.MonacoEnvironment = { getWorkerUrl: () => URL.createObjectURL(new Blob(
      ['self.MonacoEnvironment={baseUrl:' + JSON.stringify(location.origin + '/vendor/monaco/') + '};importScripts(' + JSON.stringify(base + '/base/worker/workerMain.js') + ');'],
      { type: 'text/javascript' })) };
    require.config({ paths: { vs: 'vendor/monaco/vs' } });
    require(['vs/editor/editor.main'], () => {
      monacoTheme();
      ed = monaco.editor.create($('editor'), { theme: 'ilab', automaticLayout: true, minimap: { enabled: false }, model: null,
        fontFamily: '"Geist Mono", ui-monospace, Menlo, Consolas, monospace', fontSize: 13, lineHeight: 21,
        padding: { top: 12 }, scrollBeyondLastLine: false, renderLineHighlight: 'all', overviewRulerBorder: false });
      document.fonts && document.fonts.ready.then(() => monaco.editor.remeasureFonts());
      ed.onDidChangeModelContent(() => { dirty = true; $('save-status').textContent = 'Unsaved'; clearTimeout(saveT); saveT = setTimeout(save, 800); });
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Quote, () => doRun());
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => doSubmit());
      res();
    }, rej);
  });
  return monacoP;
}
const LANG = { py: 'python', go: 'go', java: 'java', ts: 'typescript', js: 'javascript', c: 'c', h: 'c', cpp: 'cpp', cc: 'cpp', hpp: 'cpp', md: 'markdown', json: 'json', mod: 'plaintext' };
const langOf = p => LANG[(p.split('.').pop() || '').toLowerCase()] || 'plaintext';

async function openFile(p) {
  await save();
  const text = await (await api('/sets/' + cur + '/files/' + enc(p), {}, true)).text();
  await loadMonaco();
  if (models[p]) models[p].dispose();
  models[p] = monaco.editor.createModel(text, langOf(p), monaco.Uri.parse('inmemory:///' + enc(p)));
  curFile = p; dirty = false;
  ed.setModel(models[p]);
  $('save-status').textContent = 'Saved';
  renderTree();
}
async function save() {
  clearTimeout(saveT);
  if (!dirty || !curFile || !models[curFile]) return;
  dirty = false;
  try {
    await api('/sets/' + cur + '/files/' + enc(curFile), { method: 'PUT', body: models[curFile].getValue() });
    $('save-status').textContent = 'Saved';
  } catch (e) { dirty = true; $('save-status').textContent = 'Save failed: ' + e.message; }
}
function renderTree() {
  const t = $('file-tree'); t.textContent = '';
  (st.files || []).forEach(f => {
    const d = document.createElement('div');
    d.textContent = f; d.title = f; d.tabIndex = 0; d.setAttribute('role', 'treeitem'); d.dataset.testid = 'file-' + f;
    if (f === curFile) { d.className = 'sel'; d.setAttribute('aria-selected', 'true'); }
    const go = () => openFile(f).catch(e => flash(e.message, true));
    d.onclick = go; d.onkeydown = e => { if (e.key === 'Enter') go(); };
    t.appendChild(d);
  });
}

/* ---------- screens ---------- */
function screen(name) { // 'drop' | 'ready' | 'round'
  show('dropzone', name === 'drop'); show('ready', name === 'ready'); show('round', name === 'round');
  show('timer-wrap', name === 'round'); show('parts', name === 'round');
  if (name !== 'round') { clearInterval(pollT); clearInterval(tickT); }
}
async function loadSets(select) {
  const { sets } = await api('/sets');
  const p = $('set-picker'); p.textContent = '';
  sets.forEach(s => { const o = document.createElement('option'); o.value = s.name; o.textContent = s.title + ' · ' + s.status; p.appendChild(o); });
  show('set-picker', sets.length > 0);
  if (!sets.length) { cur = null; screen('drop'); return; }
  const want = [select, cur, LS.get('ilab-last')].find(n => n && sets.some(s => s.name === n)) || sets[0].name;
  p.value = want;
  await openSet(want);
}
async function openSet(name) {
  await save();
  cur = name; LS.set('ilab-last', name); $('set-picker').value = name;
  show('final', false); show('closed-bar', false);
  Object.values(models).forEach(m => m.dispose()); models = {}; curFile = null; st = null;
  ['problem', 'results', 'file-tree'].forEach(id => { $(id).textContent = ''; }); // no stale content from the previous set
  try {
    const info = await api('/sets/' + name);
    if (info.status === 'ready') return showReady(info);
    await enterRound(await api('/sets/' + name + '/state'));
  } catch (e) { screen('ready'); $('ready').innerHTML = '<div class="ready-card"><p class="err">' + esc(e.message) + '</p></div>'; }
}
const ROUND = { codebase: 'Codebase round', levelled: 'Levelled round', 'ai-assisted': 'AI-assisted round', tdd: 'TDD round', dsa: 'DSA round' };
const LANGNAME = { python: 'Python', go: 'Go', java: 'Java', typescript: 'TypeScript', javascript: 'JavaScript', c: 'C', cpp: 'C++' };
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';
function showReady(i) {
  screen('ready');
  const eyebrow = [i.company, i.role, ROUND[i.round] || i.round].filter(Boolean).map(esc).join(' · ');
  $('ready').innerHTML = '<div class="ready-card">' +
    (eyebrow ? '<div class="eyebrow">' + eyebrow + '</div>' : '') +
    '<h1>' + esc(i.title) + '</h1>' +
    '<div class="pills"><span class="pill">' + esc(LANGNAME[i.language] || i.language) + '</span><span class="pill">' + esc(cap(i.difficulty)) +
    '</span><span class="pill mono">' + esc(i.minutes) + ' min</span></div>' +
    (i.rules ? '<div class="rules md"><div class="label">Before you start</div>' + md(i.rules) + '</div>' : '') +
    '<div class="go"><button id="start-btn" class="btn btn-solid btn-lg" type="button" aria-label="Start interview">Start interview</button>' +
    '<small>The clock starts when you press Start. The problem appears then.</small></div>' +
    '<p id="start-err" class="err" role="alert"></p></div>';
  $('start-btn').onclick = async () => {
    $('start-btn').disabled = true; $('start-btn').textContent = 'Starting…';
    try { await enterRound(await api('/sets/' + cur + '/start', { method: 'POST' })); }
    catch (e) { $('start-err').textContent = e.message; $('start-btn').disabled = false; $('start-btn').textContent = 'Start interview'; }
  };
}
const EMPTY = '<p class="empty">Run your code with <kbd>Ctrl \'</kbd> or submit with <kbd>Ctrl ↵</kbd>. Results show here.</p>';
async function enterRound(state) {
  screen('round'); st = null; $('results').innerHTML = EMPTY;
  setState(state, true);
  await loadMonaco();
  show('timer-wrap', true);
  const first = st.files.find(f => f === st.run_entry) || st.files[0];
  if (first) await openFile(first); else renderTree();
  clearInterval(pollT); clearInterval(tickT);
  pollT = setInterval(poll, 5000); tickT = setInterval(tick, 250); tick();
  if (st.ended) showFinal();
}
function setState(s, force) {
  const newParts = (s.parts || []).length;
  st = s;
  deadline = Date.now() + s.left_s * 1000;   // server "now" cancels out: left_s is relative to it
  if (force || newParts !== partsSeen) { partsSeen = newParts; renderProblem(); }
  show('mytests-btn', s.has_mytests); show('submit-btn', s.has_submit); show('next-btn', s.has_next);
  $('next-bar-text').textContent = 'Show the next part now? This is logged as asked to move on.' + (s.ended ? ' It is marked after time.' : '');
  syncBar();
  if (cur) { const o = [...$('set-picker').options].find(o => o.value === cur); if (o) o.textContent = s.title + ' · ' + s.status; }
  if (s.files && $('file-tree').childElementCount !== s.files.length) renderTree();
  renderParts();
}
// "test_p2_" -> "Part 2", "test_l3_" -> "Level 3", anything else -> "Tests"
function partName(tag) { const m = /_(p|l)(\d+)_?$/i.exec(tag); return m ? (m[1].toLowerCase() === 'l' ? 'Level ' : 'Part ') + m[2] : 'Tests'; }
function renderParts() {
  const tags = st.unlocked || [];
  const done = t => { const g = (st.results || {})[t]; return g && g.status === 'graded' && g.total > 0 && g.passed === g.total; };
  const current = tags.find(t => !done(t));
  $('parts').innerHTML = tags.length < 2 && !done(tags[0]) ? '' : tags.map(t =>
    '<span class="chip ' + (done(t) ? 'done' : t === current ? 'current' : '') + '">' + (done(t) ? '✓ ' : '') + esc(partName(t)) + '</span>').join('');
}
function renderProblem() {
  let h = md(st.problem);
  (st.parts || []).forEach(p => {
    const at = (st.events || []).find(e => String(e[1]).includes('revealed ' + p.file));
    h += '<div class="part-divider">New part' + (at ? ' · ' + esc(at[0]) + ' min' : '') + '</div>' + md(p.md);
  });
  $('problem').innerHTML = h;
}
async function poll() {
  if (!cur) return;
  try { const s = await api('/sets/' + cur + '/state'); if (s.name === cur || !s.name) { const wasEnded = st && st.ended; setState(s); if (s.ended && !wasEnded) showFinal(); } } catch (e) {}
}
function tick() {
  if (!st) return;
  const left = st.ended ? Math.ceil(st.left_s) : Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  const t = $('timer');
  t.textContent = String(Math.floor(left / 60)).padStart(2, '0') + ':' + String(left % 60).padStart(2, '0');
  t.classList.toggle('low', !st.ended && left > 0 && left <= 300);
  t.classList.toggle('over', !!st.expired || (!st.ended && left === 0));
  $('timer-label').textContent = st.ended ? 'closed' : 'left';
  if (left === 0 && !st.ended) autoClose();
}

// 00:00 closes the round: save, then the same call as End. Retries on the next poll period if it fails.
let closing = false, closeTry = 0, closeErr = false;
async function autoClose() {
  if (closing || busy || Date.now() - closeTry < 5000) return;
  closing = true; closeTry = Date.now(); const name = cur;
  try {
    await save();
    const s = await api('/sets/' + name + '/end', { method: 'POST' });
    if (name !== cur) return;
    closeErr = false; setState(s); showFinal();
  } catch (e) { if (name === cur && !closeErr) { closeErr = true; $('results').innerHTML = '<p class="err">Time is up but the round could not be closed: ' + esc(e.message) + ' Retrying.</p>'; } }
  finally { closing = false; }
}
const mmss = sec => String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(Math.floor(sec % 60)).padStart(2, '0');
const closedAt = () => mmss(Math.max(0, st.minutes * 60 - st.left_s));
function syncBar() {
  const on = !!(st && st.ended) && $('final').classList.contains('hidden');
  if (on) $('closed-text').textContent = 'Round closed at ' + closedAt() + '. Anything you run, test or submit now is marked after time.';
  show('closed-bar', on);
}
function closeFinal() { show('final', false); syncBar(); }

/* ---------- actions ---------- */
function flash(msg, bad) {
  const f = $('flash'); show('flash', false); void f.offsetWidth; // hide + reflow so a repeat visibly re-shows
  f.textContent = msg; f.classList.toggle('bad', !!bad); show('flash', true);
  clearTimeout(flash.t); flash.t = setTimeout(() => show('flash', false), 5000);
}
async function guarded(label, fn) {
  if (busy || !st) return;
  busy = true;
  const bs = ['run-btn', 'mytests-btn', 'submit-btn', 'next-btn', 'end-btn', 'export-btn'].map($);
  bs.forEach(b => b.disabled = true); $('busy').textContent = label + '…';
  try { await save(); await fn(); }
  catch (e) { $('results').innerHTML = '<p class="err">' + esc(e.message) + '</p>'; }
  finally { busy = false; bs.forEach(b => b.disabled = false); $('busy').textContent = ''; }
}
const vclass = v => v === 'Accepted' ? 'pass' : /Limit/.test(v) ? 'warn' : 'fail';
const badge = v => '<span id="verdict" data-testid="verdict" class="badge ' + vclass(v) + '">' + esc(v) + '</span>';
function caseHtml(c) {
  return (c.stdout ? '<pre class="out">' + esc(c.stdout) + '</pre>' : '') +
    (c.stderr ? '<pre class="out bad">' + esc(c.stderr) + '</pre>' : '') +
    (c.truncated ? '<p class="muted">Output truncated at 64 KB.</p>' : '') +
    (!c.stdout && !c.stderr ? '<p class="muted">No output.</p>' : '');
}
function doRun() {
  guarded('Running', async () => {
    const r = await api('/sets/' + cur + '/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file: curFile, stdin: $('stdin').value }) });
    const c0 = r.stdin_case || (r.testcases || [])[0];
    let h = '<div class="res-head">' + badge(r.verdict) + lateWord(st.ended) +
      (c0 ? '<span class="meta">' + c0.ms + ' ms' + (r.memory_kb != null ? ' · ' + (r.memory_kb / 1024).toFixed(1) + ' MB' : '') +
        (r.stdin_case && r.stdin_case.exit != null ? ' · exit ' + r.stdin_case.exit : '') + '</span>' : '') + '</div>';
    if (r.compile && !r.compile.ok) h += '<pre class="out bad">' + esc(r.compile.log) + '</pre>';
    if (r.stdin_case) h += caseHtml(r.stdin_case);
    if (r.testcases && r.testcases.length) {
      h += '<div class="tbl-wrap"><table><thead><tr><th></th><th>Input</th><th>Expected</th><th>Got</th></tr></thead><tbody>' + r.testcases.map(c =>
        '<tr><td class="' + (c.pass ? 'ok" aria-label="passed">✓' : 'no" aria-label="failed">✗') + '</td><td class="mono">' + esc(c.stdin) + '</td><td class="mono">' +
        esc(c.expected) + '</td><td class="mono">' + esc(c.stdout || c.stderr) + (c.truncated ? ' (output truncated)' : '') + '</td></tr>').join('') + '</tbody></table></div>';
    }
    $('results').innerHTML = h;
  });
}
const lateWord = on => on ? '<span class="late">after time</span>' : '';
function gradeRow(tag, g, names) {
  let s = '<div class="grade"><span class="tag">' + esc(tag) + '</span>';
  if (g.status === 'graded') {
    const pct = g.total ? Math.round(100 * g.passed / g.total) : 0;
    s += '<span class="count">' + g.passed + '/' + g.total + '</span><span class="meter' + (pct === 100 ? ' full' : '') + '"><i style="width:' + pct + '%"></i></span>';
  } else s += '<span class="count warn">—</span><span class="status">' + esc(g.status) + (g.limit_s ? ' in ' + esc(g.limit_s) + ' s' : '') + '</span>';
  const last = g.last_error || g.last_line;
  if (last && (g.status !== 'graded' || g.passed < g.total)) s += '<span class="why">' + esc(last) + '</span>';
  s += lateWord(g.after_time);
  if (names && g.failed && g.failed.length) s += '<span class="names">' + esc(g.failed.join('\n')) + '</span>';
  return s + '</div>';
}
function showGrades(title, results, names) {
  const keys = Object.keys(results);
  $('results').innerHTML = '<div class="label">' + esc(title) + '</div>' + '<div class="grades">' +
    (keys.map(k => gradeRow(k, results[k], names)).join('') || '<p class="muted">No results.</p>') + '</div>';
}
function doMyTests() { guarded('Running your tests', async () => { const g = await api('/sets/' + cur + '/mytests', { method: 'POST' }); showGrades('My tests', { 'my tests': g }, true); }); }
function doSubmit() {
  if (!st || !st.has_submit) return;
  guarded('Submitting', async () => {
    const was = st.ended;
    const r = await api('/sets/' + cur + '/submit', { method: 'POST' });
    showGrades('Hidden tests', r.results, false);
    setState(r.state, (r.revealed || []).length > 0);
    if ((r.revealed || []).length) flash('New part unlocked. The problem pane has it.');
    if (r.state.ended && !was) showFinal();
  });
}
async function doExport() {
  await save();
  const r = await api('/sets/' + cur + '/export', {}, true);
  const u = URL.createObjectURL(await r.blob());
  const a = document.createElement('a'); a.href = u; a.download = 'export.zip'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 10000);
  flash('Downloaded export.zip. Send it to Claude for the debrief. A copy is in data/exports/.');
}
function showFinal() {
  if (!st) return;
  const g = st.final || {};
  const keys = Object.keys(g);
  const empty = !st.has_submit ? 'This set has no hidden tests (Run only).' : 'No final grade: ' + esc(st.final_error || 'press End to retry') + '.';
  let h = '<div class="final-card"><div><div class="label">' + esc(st.title) + '</div><h2>' + (st.expired ? "Time's up" : 'Interview ended') + '</h2></div>' +
    '<div class="grades">' + (keys.map(k => gradeRow(k, g[k], true)).join('') || '<p class="muted">' + empty + '</p>') + '</div>' +
    '<p class="muted">Closed at ' + closedAt() + ' of ' + esc(st.minutes) + ' min. Export, then send export.zip to Claude for the debrief.</p>' +
    '<div><div class="label">Where the time went</div><div class="events">' +
    (st.events || []).map(e => '<div><span>' + esc(e[0]) + '</span><span>' + esc(e[1]).replace('(after time)', '<em>(after time)</em>') + '</span></div>').join('') + '</div></div>' +
    '<div class="actions"><button id="final-export" class="btn btn-solid" type="button" aria-label="Export">Export</button>' +
    '<button id="final-close" class="btn btn-ghost" type="button">Close</button></div></div>';
  const f = $('final'); f.innerHTML = h; show('final', true); syncBar();
  $('final-export').onclick = () => doExport().catch(e => flash(e.message, true));
  $('final-close').onclick = closeFinal;
}

/* ---------- wiring ---------- */
$('run-btn').onclick = doRun;
$('mytests-btn').onclick = doMyTests;
$('submit-btn').onclick = doSubmit;
$('export-btn').onclick = () => guarded('Exporting', doExport);
$('next-btn').onclick = () => { show('next-btn', false); show('next-bar', true); $('next-no').focus(); };
$('next-no').onclick = () => { show('next-bar', false); show('next-btn', true); };
$('closed-results').onclick = showFinal;
$('next-yes').onclick = () => { show('next-bar', false); show('next-btn', true);
  guarded('Revealing', async () => { const before = (st.parts || []).length; setState(await api('/sets/' + cur + '/next', { method: 'POST' }), true); if (st.parts.length > before) flash('New part unlocked. The problem pane has it.'); }); };
$('end-btn').onclick = () => { show('end-btn', false); show('end-bar', true); $('end-no').focus(); };
$('end-no').onclick = () => { show('end-bar', false); show('end-btn', true); };
$('end-confirm').onclick = () => { show('end-bar', false); show('end-btn', true);
  guarded('Ending', async () => { setState(await api('/sets/' + cur + '/end', { method: 'POST' })); showFinal(); }); };
$('newfile-form').onsubmit = async e => {
  e.preventDefault();
  const p = $('newfile').value.trim().replace(/^\/+/, ''); if (!p) return;
  try {
    await api('/sets/' + cur + '/files/' + enc(p), { method: 'PUT', body: '' });
    $('newfile').value = '';
    if (!st.files.includes(p)) st.files.push(p);
    await openFile(p);
  } catch (err) { flash(err.message, true); }
};
$('set-picker').onchange = e => openSet(e.target.value);
document.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => setTheme(b.dataset.t)));
window.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !$('final').classList.contains('hidden')) { closeFinal(); return; }
  if (!(e.ctrlKey || e.metaKey) || !st || $('round').classList.contains('hidden')) return;
  if (e.key === "'") { e.preventDefault(); doRun(); }
  else if (e.key === 'Enter') { e.preventDefault(); doSubmit(); }
});

// drag & drop import: the only import path
let dragN = 0;
const hasFiles = e => e.dataTransfer && [...(e.dataTransfer.types || [])].includes('Files');
window.addEventListener('dragenter', e => { if (hasFiles(e)) { e.preventDefault(); dragN++; document.body.classList.add('over'); $('dropzone').classList.add('over'); } });
window.addEventListener('dragover', e => { if (hasFiles(e)) e.preventDefault(); });
window.addEventListener('dragleave', e => { if (hasFiles(e) && --dragN <= 0) { dragN = 0; document.body.classList.remove('over'); $('dropzone').classList.remove('over'); } });
window.addEventListener('drop', async e => {
  e.preventDefault(); dragN = 0; document.body.classList.remove('over'); $('dropzone').classList.remove('over');
  const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
  if (!f) return;
  $('drop-error').textContent = '';
  try {
    const { name } = await api('/import', { method: 'POST', body: await f.arrayBuffer() });
    await loadSets(name);
  } catch (err) {
    $('drop-error').textContent = err.message;
    if (cur) flash('Import failed: ' + err.message, true);
  }
});
window.addEventListener('beforeunload', () => { if (dirty) save(); });

async function health() {
  try {
    const h = await api('/health'); const m = [];
    if (!h.docker) m.push(h.error || 'Docker is unreachable. Start Docker, then reload this page.');
    Object.entries(h.images || {}).forEach(([k, v]) => { if (v === 'pulling') m.push('Preparing the ' + k + ' runner image…'); else if (v === 'missing') m.push('The ' + k + ' runner image is missing. Run ./install.sh.'); });
    $('health').textContent = m.join(' '); show('health', m.length > 0);
  } catch (e) { $('health').textContent = e.message; show('health', true); }
}
setTheme(LS.get('ilab-theme') || '');
health(); setInterval(health, 15000);
loadSets().catch(e => { screen('drop'); $('drop-error').textContent = e.message; });

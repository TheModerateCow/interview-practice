// Non-UI helpers: API calls, Monaco, labels. Ported from the old ui/app.js.

export async function api(path, opts = {}, raw) {
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
export const enc = p => p.split('/').map(encodeURIComponent).join('/');

export const LS = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };

export const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// marked is a global from /vendor/marked.min.js; without it, show the text as-is.
export const md = s => (window.marked ? window.marked.parse(String(s || '')) : '<pre>' + esc(s) + '</pre>');

export const ROUND = { codebase: 'Codebase round', levelled: 'Levelled round', 'ai-assisted': 'AI-assisted round', tdd: 'TDD round', dsa: 'DSA round' };
export const LANGNAME = { python: 'Python', go: 'Go', java: 'Java', typescript: 'TypeScript', javascript: 'JavaScript', c: 'C', cpp: 'C++' };
export const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';
// "test_p2_" -> "Part 2", "test_l3_" -> "Level 3", anything else -> "Tests"
export function partName(tag) { const m = /_(p|l)(\d+)_?$/i.exec(tag); return m ? (m[1].toLowerCase() === 'l' ? 'Level ' : 'Part ') + m[2] : 'Tests'; }
export const statusWords = s => s.status === 'running' && s.left_s != null ? Math.max(1, Math.ceil(s.left_s / 60)) + ' min left' : s.status === 'ready' ? 'not started' : s.status === 'ended' ? 'finished' : s.status;
export const mmss = sec => String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(Math.floor(sec % 60)).padStart(2, '0');
export const vclass = v => v === 'Accepted' ? 'pass' : /Limit/.test(v) ? 'warn' : 'fail';

const LANG = { py: 'python', go: 'go', java: 'java', ts: 'typescript', js: 'javascript', c: 'c', h: 'c', cpp: 'cpp', cc: 'cpp', hpp: 'cpp', md: 'markdown', json: 'json', mod: 'plaintext' };
export const langOf = p => LANG[(p.split('.').pop() || '').toLowerCase()] || 'plaintext';

/* ---------- theme, shared with Monaco ---------- */
export const darkMQ = matchMedia('(prefers-color-scheme: dark)');
function isDark() { const t = document.documentElement.dataset.theme; return t ? t === 'dark' : darkMQ.matches; }
export function monacoTheme() {
  const monaco = window.monaco;
  if (!monaco) return;
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

/* ---------- Monaco: loaded once through its AMD loader (/vendor/monaco/vs/loader.js) ---------- */
let monacoP = null;
// Resolves to the editor. on: { change, run, submit } callbacks.
export function loadMonaco(el, on) {
  if (monacoP) return monacoP;
  monacoP = new Promise((res, rej) => {
    const base = location.origin + '/vendor/monaco/vs';
    self.MonacoEnvironment = { getWorkerUrl: () => URL.createObjectURL(new Blob(
      ['self.MonacoEnvironment={baseUrl:' + JSON.stringify(location.origin + '/vendor/monaco/') + '};importScripts(' + JSON.stringify(base + '/base/worker/workerMain.js') + ');'],
      { type: 'text/javascript' })) };
    window.require.config({ paths: { vs: '/vendor/monaco/vs' } });
    window.require(['vs/editor/editor.main'], () => {
      const monaco = window.monaco;
      monacoTheme();
      const ed = monaco.editor.create(el, { theme: 'ilab', automaticLayout: true, minimap: { enabled: false }, model: null,
        fontFamily: '"Geist Mono", ui-monospace, Menlo, Consolas, monospace', fontSize: 13, lineHeight: 21,
        padding: { top: 12 }, scrollBeyondLastLine: false, renderLineHighlight: 'all', overviewRulerBorder: false });
      document.fonts && document.fonts.ready.then(() => monaco.editor.remeasureFonts());
      ed.onDidChangeModelContent(on.change);
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Quote, on.run);
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, on.submit);
      res(ed);
    }, rej);
  });
  return monacoP;
}

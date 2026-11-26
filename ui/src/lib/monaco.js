import { LS } from './util.js';
// Monaco editor: language per file, the theme built from tokens.css, and the one-time AMD load.
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

const wrapOpt = () => (LS.get('ilab-wrap') === 'on' ? 'on' : 'off');

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
        padding: { top: 12 }, scrollBeyondLastLine: false, renderLineHighlight: 'all', overviewRulerBorder: false, wordWrap: wrapOpt() });
      document.fonts && document.fonts.ready.then(() => monaco.editor.remeasureFonts());
      ed.onDidChangeModelContent(on.change);
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Quote, on.run);
      ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, on.submit);
      res(ed);
    }, rej);
  });
  return monacoP;
}

// Display only: the text, autosave, Run and Submit never see the wrap. Before the editor exists, only the choice is saved.
export function setWrap(on) { LS.set('ilab-wrap', on ? 'on' : 'off'); monacoP?.then(ed => ed.updateOptions({ wordWrap: wrapOpt() })); }

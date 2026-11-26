// Code help: Monaco providers (completion, hover, signature help) and error underlines, backed by POST /api/sets/<n>/assist.
// The language server lives in a container on the backend; if it is starting or unavailable every provider returns
// nothing, so Monaco falls back to word suggestions and the round carries on.
import { api } from './api.js';

const LANGS = ['python', 'go'];   // languages with a server; one line per language as PRs add them
const ASSIST_LINE = { python: 'Code help: suggestions from your code and Python\'s standard library, parameter hints and error underlines.',
  go: 'Code help: suggestions from your code and Go\'s standard library, parameter hints and error underlines.' };
export function assistLine(lang) {
  return ASSIST_LINE[lang] || 'Autocomplete: ' + (['javascript', 'typescript'].includes(lang)
    ? 'suggests methods and types as you type.' : 'suggests only words already in your files, not library functions or methods.');
}

const KINDS = ['', 'Text', 'Method', 'Function', 'Constructor', 'Field', 'Variable', 'Class', 'Interface', 'Module', 'Property', 'Unit', 'Value',
  'Enum', 'Keyword', 'Snippet', 'Color', 'File', 'Reference', 'Folder', 'EnumMember', 'Constant', 'Struct', 'Event', 'Operator', 'TypeParameter'];
const SEVERITY = ['', 'Error', 'Warning', 'Info', 'Hint'];

let monaco = null, ctx = null, timer = null, checkT = null;   // ctx: { set, lang, onState }

const md = c => !c ? undefined : { value: typeof c === 'string' ? c : Array.isArray(c) ? c.map(x => x.value ?? x).join('\n\n') : c.value };
const fileOf = model => model.uri.path.slice(1);
const rng = r => new monaco.Range(r.start.line + 1, r.start.character + 1, r.end.line + 1, r.end.character + 1);

function report(r) {
  const s = r.state === 'ready' ? '' : r.state;
  if (ctx && ctx.state !== s) { ctx.state = s; ctx.onState({ state: s, reason: r.reason || '' }); }
  return r.state === 'ready' ? r : null;
}

async function ask(model, op, pos, extra = {}) {
  if (!ctx || model.isDisposed() || !LANGS.includes(ctx.lang)) return null;
  const set = ctx.set;
  try {
    const r = await api('/sets/' + set + '/assist', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op, file: fileOf(model), text: model.getValue(), line: pos ? pos.lineNumber - 1 : 0, col: pos ? pos.column - 1 : 0, ...extra }),
      signal: AbortSignal.timeout(1500) });
    return ctx && ctx.set === set ? report(r) : null;
  } catch (e) { return null; }
}

function suggestion(model, pos, it) {
  const te = it.textEdit, word = model.getWordUntilPosition(pos);
  const range = te ? rng(te.range || te.replace) : new monaco.Range(pos.lineNumber, word.startColumn, pos.lineNumber, word.endColumn);
  return { label: it.label, kind: monaco.languages.CompletionItemKind[KINDS[it.kind]] ?? monaco.languages.CompletionItemKind.Text,
    detail: it.detail, documentation: md(it.documentation), insertText: te ? te.newText : it.insertText || it.label, range,
    insertTextRules: it.insertTextFormat === 2 ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet : undefined,
    sortText: it.sortText, filterText: it.filterText, preselect: it.preselect,
    additionalTextEdits: (it.additionalTextEdits || []).map(e => ({ range: rng(e.range), text: e.newText })), _lsp: it };
}

// Once, after Monaco has loaded.
export function register(m) {
  if (monaco) return;
  monaco = m;
  for (const lang of LANGS) {
  m.languages.registerCompletionItemProvider(lang, {
    triggerCharacters: ['.'],
    async provideCompletionItems(model, pos) {
      const r = await ask(model, 'complete', pos);
      const res = r && r.result;
      if (!res) return { suggestions: [] };
      return { suggestions: (res.items || res).map(i => suggestion(model, pos, i)), incomplete: !!res.isIncomplete };
    },
    async resolveCompletionItem(item) {
      const model = monaco.editor.getEditors()[0]?.getModel();
      const r = model && await ask(model, 'resolve', null, { item: item._lsp });
      const x = r && r.result;
      if (x) {
        if (x.documentation) item.documentation = md(x.documentation);
        if (x.detail) item.detail = x.detail;
        if (x.additionalTextEdits) item.additionalTextEdits = x.additionalTextEdits.map(e => ({ range: rng(e.range), text: e.newText }));
      }
      return item;
    },
  });
  m.languages.registerHoverProvider(lang, {
    async provideHover(model, pos) {
      const r = await ask(model, 'hover', pos);
      const h = r && r.result;
      return h && h.contents ? { range: h.range && rng(h.range), contents: [md(h.contents)] } : null;
    },
  });
  m.languages.registerSignatureHelpProvider(lang, {
    signatureHelpTriggerCharacters: ['(', ','], signatureHelpRetriggerCharacters: [')'],
    async provideSignatureHelp(model, pos) {
      const r = await ask(model, 'signature', pos);
      const h = r && r.result;
      if (!h || !h.signatures || !h.signatures.length) return null;
      const sigs = h.signatures.map(s => ({ label: s.label, documentation: md(s.documentation), activeParameter: s.activeParameter,
        parameters: (s.parameters || []).map(p => ({ label: p.label, documentation: md(p.documentation) })) }));
      return { value: { signatures: sigs, activeSignature: h.activeSignature || 0, activeParameter: h.activeParameter ?? 0 }, dispose() {} };
    },
  });
  }
}

// Round entered. onState({state, reason}) feeds the toolbar line.
export function attach(set, lang, onState) {
  detach(true);
  if (!LANGS.includes(lang)) return;
  ctx = { set, lang, onState, state: '' };
  // While starting, ask again every second; while unavailable, every 15 s (the server retries after 30 s).
  let tick = 0;
  timer = setInterval(() => {
    const m = monaco && monaco.editor.getEditors()[0]?.getModel();
    if (m && (ctx.state === 'starting' || (ctx.state === 'unavailable' && ++tick % 15 === 0))) check(m);
  }, 1000);
}

// Round left: end the session and clear what we drew.
export function detach(quiet) {
  clearInterval(timer); clearTimeout(checkT);
  if (ctx && !quiet) fetch('/api/sets/' + ctx.set + '/assist', { method: 'POST', headers: { 'X-ILab': '1', 'Content-Type': 'application/json' }, body: '{"op":"stop"}', keepalive: true }).catch(() => {});
  if (monaco) monaco.editor.getModels().forEach(m => monaco.editor.setModelMarkers(m, 'ilab-assist', []));
  if (ctx) ctx.onState({ state: '', reason: '' });
  ctx = null;
}

async function check(model) {
  const r = await ask(model, 'check');
  if (!r || model.isDisposed()) return;
  monaco.editor.setModelMarkers(model, 'ilab-assist', (r.diagnostics || []).map(d => ({
    severity: monaco.MarkerSeverity[SEVERITY[d.severity || 1]], message: d.message, source: d.source, code: d.code && String(d.code),
    startLineNumber: d.range.start.line + 1, startColumn: d.range.start.character + 1, endLineNumber: d.range.end.line + 1, endColumn: d.range.end.character + 1 })));
}

// A file opened: check it now (this also starts the server), and again 0.5 s after typing stops.
export function watch(model) {
  if (!ctx) return;
  model.onDidChangeContent(() => { clearTimeout(checkT); checkT = setTimeout(() => ctx && check(model), 500); });
  check(model);
}

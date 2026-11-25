// Resizable panes: pure limits + the `splitter` action. Kept apart from lib.js so node can test it.
export const PANE_DEF = { files: 190, problem: 360, bottom: null };   // bottom null = 36% of the editor column
const GAP = 12, EDITOR_MIN = 320;

// [min, max] in px. ctx: w = window width, h = editor column height, files/problem = the other panes' widths.
export function paneLimits(key, { w, h, files, problem }) {
  if (key === 'files') return [120, Math.max(120, Math.min(480, w - problem - GAP - EDITOR_MIN))];
  if (key === 'problem') return [220, Math.max(220, Math.min(0.6 * w, w - files - GAP - EDITOR_MIN))];
  return [80, Math.max(80, 0.7 * h)];
}
export function clampSize(key, v, ctx) {
  const [lo, hi] = paneLimits(key, ctx);
  return Math.round(Math.min(hi, Math.max(lo, v)));
}
// Saved value -> sizes; anything bad falls back to the defaults.
export function parsePanes(raw) {
  let o = {};
  try { o = JSON.parse(raw) || {}; } catch (e) {}
  const num = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v : d);
  return { files: num(o.files, PANE_DEF.files), problem: num(o.problem, PANE_DEF.problem), bottom: num(o.bottom, null) };
}

// o: { axis: 'x'|'y', sign: +1|-1 (+1 = the pane grows when the border moves right/down), cur(), set(px), reset(), done() }
export function splitter(node, o) {
  let from = null;
  const pos = e => (o.axis === 'x' ? e.clientX : e.clientY);
  const down = e => {
    if (e.button) return;
    node.setPointerCapture(e.pointerId); e.preventDefault();
    from = { p: pos(e), v: o.cur() }; document.body.classList.add('resizing');
  };
  const move = e => { if (from) o.set(from.v + o.sign * (pos(e) - from.p)); };
  const up = () => { if (!from) return; from = null; document.body.classList.remove('resizing'); o.done(); };
  const keys = o.axis === 'x' ? { ArrowLeft: -1, ArrowRight: 1 } : { ArrowUp: -1, ArrowDown: 1 };
  const key = e => {
    if (e.key in keys) o.set(o.cur() + o.sign * keys[e.key] * (e.shiftKey ? 64 : 16));
    else if (e.key === 'Home') o.set(-Infinity);
    else if (e.key === 'End') o.set(Infinity);
    else return;
    e.preventDefault(); o.done();
  };
  const dbl = () => { o.reset(); o.done(); };
  node.addEventListener('pointerdown', down); node.addEventListener('pointermove', move);
  node.addEventListener('pointerup', up); node.addEventListener('pointercancel', up);
  node.addEventListener('keydown', key); node.addEventListener('dblclick', dbl);
  return { update(n) { o = n; } };
}

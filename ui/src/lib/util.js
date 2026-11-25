// Small helpers: localStorage, escaping/markdown, labels and formatting.
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

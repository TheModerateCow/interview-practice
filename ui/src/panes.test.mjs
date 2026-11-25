// node ui/src/panes.test.mjs
import assert from 'node:assert/strict';
import { clampSize, parsePanes, PANE_DEF } from './panes.js';
const c = { w: 1440, h: 600, files: 190, problem: 360 };
assert.equal(clampSize('files', 10, c), 120);
assert.equal(clampSize('files', 9999, c), 480);
assert.equal(clampSize('files', 9999, { ...c, w: 900 }), 900 - 360 - 12 - 320);       // editor keeps 320
assert.equal(clampSize('problem', 10, c), 220);
assert.equal(clampSize('problem', 9999, c), 864);                                       // 60% of the window
assert.equal(clampSize('problem', 9999, { ...c, w: 1000 }), 1000 - 190 - 12 - 320);
assert.equal(clampSize('bottom', 5, c), 80);
assert.equal(clampSize('bottom', 9999, c), 420);                                        // 70% of the column
assert.equal(clampSize('bottom', 200, c), 200);
assert.deepEqual(parsePanes(null), PANE_DEF);
assert.deepEqual(parsePanes('{bad'), PANE_DEF);
assert.deepEqual(parsePanes('{"files":"x","problem":300,"bottom":150}'), { files: 190, problem: 300, bottom: 150 });
console.log('PASS panes');

# Loading

A wait the candidate should see: a small ring turning beside words that say what is happening. It appears only once the wait passes 300 ms, so quick actions never flicker.

- Provide: `.loading` with the words, ending in "…": "Running hidden tests…". Inline, the ring takes the colour of its text, so it works in the toolbar, inside a solid button and in a toast. Add `block` to centre it in a pane or the page, in `fg-3`.
- One loader per wait, where the answer will appear: the results pane for Run, My tests and Submit; the toolbar status for End, time up, Next part and Export; the page while a set opens; a cover over the editor while it loads; a toast while a zip imports. Never a ring without words.
- Give it `role="status"` (or put it in a live region) so screen readers hear the words.
- The ring is the only continuous motion in the system. With `prefers-reduced-motion` it stands still and the words carry the meaning.

<script>
  // Header part of the round: part chips and the timer.
  import { mmss, partName } from '../../lib/util.js';
  import { round, secondsLeft } from './round.svelte.js';
  let { shown } = $props();

  const st = $derived(round.st);
  const left = $derived(secondsLeft());
  const done = t => { const g = (st?.results || {})[t]; return g && g.status === 'graded' && g.total > 0 && g.passed === g.total; };
  const chips = $derived.by(() => {
    const tags = st?.unlocked || [];
    if (tags.length < 2 && !done(tags[0])) return [];
    const current = tags.find(t => !done(t));
    return tags.map(t => ({ label: (done(t) ? '✓ ' : '') + partName(t), cls: done(t) ? 'done' : t === current ? 'current' : '' }));
  });
</script>

<div id="parts" class="parts" class:hidden={!shown} aria-label="Parts">
  {#each chips as c}<span class="chip {c.cls}">{c.label}</span>{/each}
</div>
<div id="timer-wrap" class="timer-wrap" class:hidden={!shown}><span id="timer-label" class="label">{st?.ended ? 'closed' : 'left'}</span><span id="timer" class="timer"
  class:low={!!st && !st.ended && left > 0 && left <= 300} class:over={!!st && (!!st.expired || (!st.ended && left === 0))}
  role="timer" aria-label="Time left">{st ? mmss(left) : '--:--'}</span></div>

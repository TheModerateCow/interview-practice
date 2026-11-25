<script>
  // The problem pane. Levels shown as tabs: problem.md (first tag) plus each revealed part, in order. Locked levels have no tab.
  import { app } from '../../app.svelte.js';
  import { LS, md, mmss, partName } from '../../lib/util.js';
  import { round } from './round.svelte.js';

  const levels = $derived.by(() => {
    const st = round.st;
    if (!st) return [];
    const tags = st.unlocked || [];
    return [{ name: partName(tags[0]), html: md(st.problem), at: null }].concat((st.parts || []).map((p, i) => {
      const e = (st.events || []).find(e => String(e[1]).includes('revealed ' + p.file));
      return { name: tags[i + 1] ? partName(tags[i + 1]) : 'Part ' + (i + 2), html: md(p.md), at: e ? mmss(e[0] * 60) : '' };
    }));
  });
  // levelSel: the tab picked by hand or by an unlock; -1 = newest. Remembered per set.
  let levelSel = $state(-1), seenLevels = -1;
  const lvl = $derived(Math.max(0, Math.min(levelSel < 0 ? levels.length - 1 : levelSel, levels.length - 1)));
  function pickLevel(i) { levelSel = i; LS.set('ilab.level.' + app.cur, String(i)); }
  $effect(() => { const cur = app.cur; seenLevels = -1; levelSel = Number(LS.get('ilab.level.' + cur) ?? -1); });
  $effect(() => {   // a new unlock opens its tab; the first load of a set keeps the remembered one
    const n = levels.length;
    if (n && seenLevels >= 0 && n > seenLevels) pickLevel(n - 1);
    if (n) seenLevels = n;
  });
  function levelKey(e) {
    const n = levels.length, k = { ArrowRight: lvl + 1, ArrowLeft: lvl - 1, Home: 0, End: n - 1 }[e.key];
    if (k === undefined) return;
    e.preventDefault(); const i = (k + n) % n; pickLevel(i);
    document.querySelector('.level-tab[data-level="' + i + '"]')?.focus();
  }
</script>

<section id="problem" class="md" aria-label="Problem">
  {#if levels.length > 1}
    <div id="level-tabs" role="tablist" aria-label="Levels">
      {#each levels as l, i}
        <button class="level-tab" role="tab" id="level-tab-{i}" data-level={i} aria-selected={i === lvl} aria-controls="level-panel"
          tabindex={i === lvl ? 0 : -1} onclick={() => pickLevel(i)} onkeydown={levelKey}>{l.name}</button>
      {/each}
    </div>
    {#if lvl > 0 && levels[lvl].at}<p class="level-at">Unlocked at {levels[lvl].at}</p>{/if}
  {/if}
  <div id="level-panel" role="tabpanel" aria-labelledby={levels.length > 1 ? 'level-tab-' + lvl : null}>{@html levels[lvl]?.html || ''}</div>
</section>

<script>
  // A select-only combobox (WAI-ARIA APG pattern): a button that opens a listbox. Focus stays on the button;
  // the active option is announced through aria-activedescendant.
  // options: [{ value, label, meta? }]; onchange(value) runs only when the choice changes.
  import { tick } from 'svelte';
  let { id, label, options, value, onchange } = $props();
  let open = $state(false), active = $state(-1), list;
  const current = $derived(options.find(o => o.value === value));
  const oid = i => `${id}-opt-${i}`;

  async function move(i) {
    active = Math.max(0, Math.min(options.length - 1, i));
    await tick();
    list?.children[active]?.scrollIntoView({ block: 'nearest' });
  }
  function show() { open = true; move(options.findIndex(o => o.value === value)); }
  function choose(i) {
    open = false;
    const o = options[i];
    if (o && o.value !== value) onchange(o.value);
  }

  function onkeydown(e) {
    if (!open) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) { e.preventDefault(); show(); }
      return;
    }
    switch (e.key) {
      case 'ArrowDown': move(active + 1); break;
      case 'ArrowUp': move(active - 1); break;
      case 'Home': move(0); break;
      case 'End': move(options.length - 1); break;
      case 'Enter': case ' ': choose(active); break;
      case 'Escape': open = false; break;
      case 'Tab': choose(active); return;   // pick, and let Tab move focus on
      default: return;
    }
    e.preventDefault();
  }
</script>

<div class="dropdown">
  <button {id} type="button" class="dropdown-btn" role="combobox" aria-label={label} aria-haspopup="listbox"
    aria-expanded={open} aria-controls="{id}-list" aria-activedescendant={open && active >= 0 ? oid(active) : undefined}
    onclick={() => (open ? (open = false) : show())} {onkeydown} onblur={() => (open = false)}>
    <span class="dropdown-value">{current?.label ?? ''}</span>
    {#if current?.meta}<span class="dropdown-meta">{current.meta}</span>{/if}
  </button>
  {#if open}
    <!-- pointerdown keeps focus on the button, so its blur only fires for clicks outside -->
    <ul class="dropdown-list" id="{id}-list" role="listbox" aria-label={label} bind:this={list} onpointerdown={e => e.preventDefault()}>
      {#each options as o, i (o.value)}
        <li id={oid(i)} role="option" aria-selected={o.value === value} data-value={o.value} class:active={i === active}
          onpointerenter={() => (active = i)} onclick={() => choose(i)}>
          <span>{o.label}</span>{#if o.meta}<span class="dropdown-meta">{o.meta}</span>{/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

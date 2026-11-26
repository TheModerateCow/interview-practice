// Native top-layer UI. modal: <dialog use:modal={open} onclose={...}> opens it with showModal(): the page behind is
// inert, Tab stays inside, Escape closes it (sync your state in onclose, which also fires for Escape), focus goes back.
export function modal(node, open) {
  const set = o => { if (o && !node.open) node.showModal(); else if (!o && node.open) node.close(); };
  set(open);
  return { update: set };
}
// popover="manual" + use:onTop: a toast shown after a modal opened stays above it (top layer, latest on top).
export const onTop = node => { node.showPopover?.(); };

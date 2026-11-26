# Dropdown

Pick one value from a list: the set picker in the header. It replaces the browser's own `select`, so it looks the same in every browser and theme.

- Provide: `.dropdown` holding a `.dropdown-btn` (`role="combobox"`, `aria-haspopup="listbox"`, `aria-expanded`) that shows the current value, and, while open, a `.dropdown-list` (`role="listbox"`) of `li role="option"` rows. Each row has the label and, optionally, a `.dropdown-meta` word in `fg-3` (the set's status).
- The chosen row is `fg` at weight 500 (`aria-selected="true"`); the row under the pointer or keyboard is `active` on `surface-2`. The chevron is drawn with a border and turns up while open: no icon.
- Keyboard: ↓ ↑ Enter or Space opens; ↓ ↑ Home End move; Enter or Space picks; Escape closes without a change; Tab picks and moves on. Focus stays on the button and the active row is announced through `aria-activedescendant`.
- The list is a bordered `bg` panel under the button, never a shadow, at most 360px tall and scrolling beyond that.
- Motion: the list fades in over `dur` and closes at once; the chevron turns over `dur`.

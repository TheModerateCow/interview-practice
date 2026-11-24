# CodeEditor

The Monaco editor theme, built at runtime from the `code-*` tokens so it follows the light and dark themes.

- Provide: Monaco with `fontFamily` Geist Mono, 13px / 21px line height, no minimap. Map tokens: keyword → `code-keyword`, string → `code-string`, number → `code-number`, comment → `code-comment` (italic), type → `code-type`, identifier → `code-function`; background `code-bg`, current line `code-line-hl`, selection `code-selection`, cursor `accent`, line numbers `fg-3`.
- Re-define the theme when the person switches Light/Dark or the system theme changes.

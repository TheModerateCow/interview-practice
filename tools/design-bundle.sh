#!/usr/bin/env bash
# Rebuild the design system's components/bundle.css from the app's CSS: the shared components of
# ui/src/styles/tokens.css (from "base" on) plus the app layer ui/src/styles/style.css. Run after changing either file.
set -euo pipefail
cd "$(dirname "$0")/.."
{ echo '/* Interview Lab components: ui/src/styles/tokens.css components + ui/src/styles/style.css (the app layout), verbatim. Uses only tokens.css custom properties. Rebuilt by tools/design-bundle.sh. */'
  sed -n '/^\/\* ---------- base/,$p' ui/src/styles/tokens.css | sed 's/^body { background/html, body { margin: 0; } body { background/'
  echo '/* ---------- app layer: ui/src/styles/style.css ---------- */'
  cat ui/src/styles/style.css
} > design/system/project/components/bundle.css

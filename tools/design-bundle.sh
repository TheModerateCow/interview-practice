#!/usr/bin/env bash
# Rebuild the design system's components/bundle.css from the app's CSS: the shared components of
# ui/tokens.css (from "base" on) plus the app layer ui/style.css. Run after changing either file.
set -euo pipefail
cd "$(dirname "$0")/.."
{ echo '/* Interview Lab components: ui/tokens.css components + ui/style.css (the app layout), verbatim. Uses only tokens.css custom properties. Rebuilt by tools/design-bundle.sh. */'
  sed -n '/^\/\* ---------- base/,$p' ui/tokens.css | sed 's/^body { background/html, body { margin: 0; } body { background/'
  echo '/* ---------- app layer: ui/style.css ---------- */'
  cat ui/style.css
} > design/system/project/components/bundle.css

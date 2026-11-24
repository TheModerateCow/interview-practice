#!/usr/bin/env bash
# Playwright e2e in the official image against http://127.0.0.1:8765.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
mkdir -p tests/out
SRC=tests/sets/_zips/rate-limiter-py.zip
[ -f "$SRC" ] || { echo "SKIP e2e: $SRC missing"; exit 0; }
export E2E_NAME="e2e-$(date +%s)"
export E2E_NAME_1M="$E2E_NAME-1m"
python3 - "$SRC" "tests/out/e2e-set.zip" "$E2E_NAME" <<'PY'
import sys, zipfile, json
src, dst, name = sys.argv[1:]
zi = zipfile.ZipFile(src)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
    for i in zi.infolist():
        d = zi.read(i)
        if i.filename.split("/")[-1] == "manifest.json" and i.filename.count("/") <= 1:
            m = json.loads(d); m["name"] = name; d = json.dumps(m).encode()
        zo.writestr(i.filename, d)
PY
python3 - "$SRC" "tests/out/e2e-set-1m.zip" "$E2E_NAME_1M" 1 <<'PY'
import sys, zipfile, json
src, dst, name, minutes = sys.argv[1:]
zi = zipfile.ZipFile(src)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
    for i in zi.infolist():
        d = zi.read(i)
        if i.filename.split("/")[-1] == "manifest.json" and i.filename.count("/") <= 1:
            m = json.loads(d); m["name"] = name; m["minutes"] = int(minutes); d = json.dumps(m).encode()
        zo.writestr(i.filename, d)
PY
docker run --rm --network host --ipc=host --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e E2E_NAME -e E2E_NAME_1M -e E2E_ZIP=/work/tests/out/e2e-set.zip -e E2E_ZIP_1M=/work/tests/out/e2e-set-1m.zip -v "$ROOT":/work \
  mcr.microsoft.com/playwright:v1.56.0-noble bash -ec '
mkdir -p /tmp/pw && cd /tmp/pw
npm init -y >/dev/null && npm i @playwright/test@1.56.0 >/dev/null
cp /work/tests/e2e.spec.mjs .
cat > playwright.config.mjs <<CFG
export default { testMatch: "e2e.spec.mjs", timeout: 300000, workers: 1, reporter: "line",
  use: { headless: true, viewport: { width: 1400, height: 900 }, acceptDownloads: true } };
CFG
npx playwright test --config playwright.config.mjs
'
python3 - tests/out/e2e-export.zip <<'PY'
import json, sys, zipfile
z = zipfile.ZipFile(sys.argv[1]); names = z.namelist()
assert any(n.startswith("submission/") for n in names), names
assert any(n.startswith("final/") for n in names), names  # needs PR 2
for f in ("session.json", "results.json", "manifest.json"): assert f in names, (f, names)
ev = " ".join(e[1] for e in json.loads(z.read("session.json"))["events"])
assert "start" in ev and "end" in ev and "revealed p2.md" in ev, ev
assert "(after time)" not in ev, ev
print("PASS export.zip contents:", sorted(n for n in names if "/" not in n), "+ submission/ + final/")
PY


#!/usr/bin/env bash
# Full acceptance run. Usage: tests/run_all.sh [--clean]
set -uo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--clean" ]; then
  docker compose down --remove-orphans || true
  docker rmi -f ilab-python:3.15.2-pytest9.2.0 2>/dev/null || true
  docker rmi -f ilab-nginx ilab-backend 2>/dev/null || true
  # Runner images too, so the backend's auto-pull of missing images is exercised.
  sed -n 's/.*os\.environ\.get("ILAB_IMG_[A-Z]*", *"\([^"]*\)").*/\1/p' backend/runner.py | sort -u | grep -v '^ilab-' | xargs -r docker rmi -f 2>/dev/null || true
  for v in $(docker volume ls -q | grep -E '(^|_)ilab-go-cache$' || true); do docker volume rm "$v" || true; done
  docker compose up -d --build || { echo "compose up failed"; exit 1; }
fi

echo "waiting for health (up to 10 min)..."
ok=0
for _ in $(seq 1 120); do
  h=$(curl -s -H 'X-ILab: 1' http://127.0.0.1:8765/api/health || true)
  if echo "$h" | grep -Eq '"docker": *true' && ! echo "$h" | grep -Eq '"(pulling|missing)"'; then ok=1; break; fi
  sleep 5
done
[ $ok = 1 ] || { echo "FAIL: health never became ready: $h"; exit 1; }

fail=0; summary=""
step() { # name, command...
  local n=$1; shift
  if "$@"; then summary="$summary\nPASS $n"; else summary="$summary\nFAIL $n"; fail=1; fi
}
gate() {
  local out
  out=$(docker compose run --rm -T -v "$PWD/tests/sets/$1:/set:ro" backend python3 gate.py /set 2>&1); echo "$out" | tail -5
  echo "$out" | grep -q "GATE PASS"
}
for d in tests/sets/*/; do
  n=$(basename "$d"); [ "$n" = "_zips" ] && continue
  step "gate $n" gate "$n"
done
step api_test python3 tests/api_test.py
step e2e tests/e2e.sh
echo; echo "=== summary ==="; printf '%b\n' "$summary"
exit $fail

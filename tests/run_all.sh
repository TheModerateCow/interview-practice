#!/usr/bin/env bash
# Full acceptance run on the isolated test stack (tests/stack.sh), built from this checkout and removed at the end.
# The dev stack on :8765 and data/ are never touched. Usage: tests/run_all.sh [--clean]
#   --clean  first remove the test stack's own images and Go cache, so everything it uses is rebuilt from scratch
set -uo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--clean" ]; then
  tests/stack.sh down >/dev/null 2>&1 || true
  docker rmi -f ilab-test-nginx ilab-test-backend 2>/dev/null || true
  docker volume rm ilab-test-go-cache 2>/dev/null || true
fi
trap 'tests/stack.sh down >/dev/null 2>&1; echo "test stack removed"' EXIT
tests/stack.sh up || exit 1

fail=0; summary=""
step() { # name, command...
  local n=$1; shift
  if "$@"; then summary="$summary\nPASS $n"; else summary="$summary\nFAIL $n"; fail=1; fi
}
gate() {
  local out
  out=$(tests/stack.sh compose run --rm -T -v "$PWD/tests/sets/$1:/set:ro" backend python3 gate.py /set 2>&1); echo "$out" | tail -5
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

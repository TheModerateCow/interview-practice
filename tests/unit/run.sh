#!/usr/bin/env bash
# Backend unit tests: every tests/unit/test_*.py, no Docker, a few seconds. Needs backend/requirements.txt (Flask).
# Each file is a plain script that exits non-zero on failure. Usage: tests/unit/run.sh
cd "$(dirname "$0")/../.." || exit 2
fail=0
for f in tests/unit/test_*.py; do
  if out=$(python3 "$f" 2>&1); then echo "$out"; else echo "$out"; echo "FAIL $f"; fail=1; fi
done
[ $fail = 0 ] && echo "unit: all passed" || echo "unit: FAILED"
exit $fail

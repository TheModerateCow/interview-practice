#!/usr/bin/env bash
# The isolated test stack. Usage: tests/stack.sh up | down | compose <args...>
#   up       rebuild from this checkout, start on 127.0.0.1:$ILAB_TEST_PORT (8766) with an empty data folder, wait for health
#   down     stop and remove it, and delete its data folder
#   compose  run any docker compose command against it (e.g. `tests/stack.sh compose logs backend`)
set -euo pipefail
cd "$(dirname "$0")/.."
export ILAB_TEST_PORT=${ILAB_TEST_PORT:-8766} ILAB_TEST_DATA="$PWD/tests/out/stack-data"
dc() { docker compose -p ilab-test -f docker-compose.yml -f tests/compose.test.yml "$@"; }
case "${1:-}" in
  up)
    dc down --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$ILAB_TEST_DATA"; mkdir -p "$ILAB_TEST_DATA"
    dc up -d --build --quiet-pull
    for _ in $(seq 1 120); do
      h=$(curl -s -H 'X-ILab: 1' "http://127.0.0.1:$ILAB_TEST_PORT/api/health" || true)
      if echo "$h" | grep -Eq '"docker": *true' && ! echo "$h" | grep -Eq '"(pulling|missing)"'; then
        echo "test stack up on 127.0.0.1:$ILAB_TEST_PORT"; exit 0
      fi
      sleep 2
    done
    echo "test stack never became healthy: ${h:-no answer}"; exit 1 ;;
  down) dc down --remove-orphans; rm -rf "$ILAB_TEST_DATA" ;;
  compose) shift; dc "$@" ;;
  *) echo "usage: tests/stack.sh up | down | compose <args...>"; exit 2 ;;
esac

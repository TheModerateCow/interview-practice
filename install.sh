#!/usr/bin/env bash
# Install / update Interview Lab. Idempotent.
set -euo pipefail
cd "$(dirname "$0")"

command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin not found" >&2; exit 1; }

mkdir -p data
docker compose up -d --build
docker compose build ilab-python

# Runner images: read the defaults from backend/runner.py so a pin needs one edit.
images=$(sed -n 's/.*os\.environ\.get("ILAB_IMG_[A-Z]*", *"\([^"]*\)").*/\1/p' backend/runner.py | sort -u | grep -v '^ilab-' || true)
for img in $images; do
  echo "pulling $img"
  docker pull "$img"
done

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/interview-lab.desktop" <<DESK
[Desktop Entry]
Name=Interview Lab
Exec=xdg-open http://127.0.0.1:8765
Type=Application
Icon=applications-development
Terminal=false
DESK

echo "waiting for the backend..."
for _ in $(seq 1 120); do
  h=$(curl -s -H 'X-ILab: 1' http://127.0.0.1:8765/api/health || true)
  if echo "$h" | grep -Eq '"docker": *true' && ! echo "$h" | grep -Eq '"(pulling|missing)"'; then
    echo "Interview Lab is ready: http://127.0.0.1:8765"
    exit 0
  fi
  sleep 5
done
echo "timed out waiting for /api/health; last: $h" >&2
exit 1

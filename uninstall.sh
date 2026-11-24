#!/usr/bin/env bash
# Remove Interview Lab containers, images built here, go cache volume and launcher. Keeps data/.
# --images also removes the shared base images (golang, temurin, gcc, node).
set -euo pipefail
cd "$(dirname "$0")"

base_images=$(sed -n 's/.*os\.environ\.get("ILAB_IMG_[A-Z]*", *"\([^"]*\)").*/\1/p' backend/runner.py | sort -u | grep -v '^ilab-' || true)

docker compose down --remove-orphans --rmi local || true
docker rmi ilab-python:3.15.2-pytest9.2.0 2>/dev/null || true
for v in $(docker volume ls -q | grep -E '(^|_)ilab-go-cache$' || true); do docker volume rm "$v" || true; done
rm -f "$HOME/.local/share/applications/interview-lab.desktop"

if [ "${1:-}" = "--images" ]; then
  for img in $base_images; do docker rmi "$img" || true; done
fi
echo "Removed. Your sessions in $PWD/data were KEPT (delete that folder yourself if you want them gone)."

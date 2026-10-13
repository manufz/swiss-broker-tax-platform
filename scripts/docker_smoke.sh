#!/usr/bin/env bash
set -euo pipefail
image="${1:?Pass the image to test}"
task_port="${SMOKE_PORT:-18080}"
task_container="swiss-tax-smoke-${RANDOM}"
cleanup() { docker rm -f "$task_container" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run --detach --rm --name "$task_container" --platform linux/amd64 \
  -p "127.0.0.1:${task_port}:8000" \
  -v "$PWD/tests/fixtures/kursliste:/data/kursliste:ro" \
  -e KURSLISTE_DIR=/data/kursliste "$image" >/dev/null
for _ in {1..60}; do
  if curl -fsS "http://127.0.0.1:${task_port}/ready" >/dev/null 2>&1; then break; fi
  sleep 1
done
test "$(docker exec "$task_container" id -u)" = "10001"
python3 scripts/smoke.py --base-url "http://127.0.0.1:${task_port}"

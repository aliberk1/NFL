#!/bin/sh
# End-to-end drill in an isolated Compose project: start, backup, data loss, restore, update, rollback.
set -eu
export COMPOSE_PROJECT_NAME=nfl-drill NFL_UI_PORT=18501 NFL_API_PORT=18000
export NFL_LLM_API_KEY= NFL_LLM_MODEL=
trap 'docker compose logs --tail 50; docker compose down -v' EXIT

up() {
    export NFL_IMAGE_TAG="$1"
    docker compose up -d --no-build --wait --wait-timeout 180
}
check() {
    curl -fsS http://127.0.0.1:18501/_stcore/health
    curl -fsS http://127.0.0.1:18000/ready | grep '"demo":true'
    curl -fsS "http://127.0.0.1:18000/players?name=Kurgusal" | grep "Kurgusal Oyuncu 01" >/dev/null
    test "$(docker compose exec -T ui printenv APP_VERSION)" = "$NFL_IMAGE_TAG"
}
run() { docker compose run --rm --no-deps -T -e NFL_DEMO_MODE=0 ui "$@"; }

echo "== documented single command"
export NFL_IMAGE_TAG=drill-1
docker compose up --build -d --wait --wait-timeout 300
check
test "$(docker compose exec -T ui id -u)" = 10001
docker compose exec -T ui sh -c "test ! -e reports && test ! -e submission_mirror && test ! -e .git && test ! -e .env"

echo "== chat is off without secrets"
test "$(curl -s -o /dev/null -w "%{http_code}" -H "content-type: application/json" -d "{\"question\":\"test\"}" http://127.0.0.1:18000/chat)" = 400

echo "== backup, data loss, restore"
run python -m pipelines.backup create /data/backups/drill.zip
docker compose stop
run sh -c "echo broken > /data/curated/nfl.duckdb"
if run python -c "from app import analytics; analytics.query('SELECT 1 FROM players')"; then
    echo "corruption was not detected"
    exit 1
fi
run python -m pipelines.backup restore /data/backups/drill.zip
up drill-1
check

echo "== update to a new version, then roll back"
export NFL_IMAGE_TAG=drill-2
docker compose build ui
up drill-2
check
up drill-1
check
echo "DRILL PASSED"

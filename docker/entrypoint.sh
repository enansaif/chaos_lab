#!/bin/bash
set -e

wait_for() {
    local host="$1"
    local port="$2"
    local name="$3"
    local retries=30
    local wait=2

    echo "Waiting for ${name} at ${host}:${port}..."
    for i in $(seq 1 $retries); do
        if python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('${host}', ${port})); s.close()" 2>/dev/null; then
            echo "${name} is ready."
            return 0
        fi
        echo "Attempt ${i}/${retries}: ${name} not ready, sleeping ${wait}s..."
        sleep $wait
    done
    echo "ERROR: ${name} did not become ready in time."
    exit 1
}

wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
wait_for "redis" "6379" "Redis"

if [ "${CELERY_BROKER_BACKEND:-redis}" = "rabbitmq" ]; then
    wait_for "rabbitmq" "5672" "RabbitMQ"
fi

python manage.py migrate --noinput

ROLE="${SERVICE_ROLE:-api}"

case "$ROLE" in
    api)
        exec uvicorn config.asgi:application \
            --host 0.0.0.0 \
            --port 8000 \
            --workers "${UVICORN_WORKERS:-4}"
        ;;
    worker)
        exec celery -A config worker -l INFO -c "${CELERY_CONCURRENCY:-4}"
        ;;
    beat)
        exec celery -A config beat -l INFO
        ;;
    *)
        echo "Unknown SERVICE_ROLE: $ROLE"
        exit 1
        ;;
esac

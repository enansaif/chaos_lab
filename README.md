# Django Distributed Systems Load Lab

A Dockerized modular Django monolith for learning backend optimization, caching, Celery brokers, and distributed-system behavior under API load.

## Quick start

```bash
cp .env.example .env
make up
make seed
curl http://localhost/api/v1/system/config/
```

If Postgres fails with password authentication errors, an old volume may exist from a prior project. Reset with `docker compose down -v` and run `make up` again.

Open API docs at http://localhost/api/docs/

## Stack

| Component | Purpose |
|-----------|---------|
| Nginx | Reverse proxy, optional rate limiting |
| Uvicorn | ASGI server for Django |
| PostgreSQL | Primary datastore |
| Redis | Cache (DB 1) + optional Celery broker (DB 0) + results (DB 2) |
| RabbitMQ | Alternative Celery broker |
| Celery | Async order processing |
| OpenTelemetry | Traces and metrics from Django/Celery |
| Loki + Alloy | Centralized container logs |
| Tempo | Trace storage |
| Prometheus | Metrics storage |
| Grafana | Dashboards and Explore UI |

See [OBSERVABILITY.md](OBSERVABILITY.md) for logs, traces, and metrics guide.

## Configuration toggles

All toggles live in `.env`:

| Variable | Values | Effect |
|----------|--------|--------|
| `CACHE_ENABLED` | `true` / `false` | Redis cache vs DummyCache |
| `CELERY_BROKER_BACKEND` | `redis` / `rabbitmq` | Celery message broker |
| `UVICORN_WORKERS` | integer | API worker processes |
| `CELERY_CONCURRENCY` | integer | Celery worker concurrency |
| `DATABASE_CONN_MAX_AGE` | seconds | DB connection pooling |
| `NGINX_RATE_LIMIT` | req/s or `0` | Rate limit (requires nginx restart) |
| `OTEL_ENABLED` | `true` / `false` | OpenTelemetry instrumentation |
| `OTEL_TRACES_SAMPLER_ARG` | `0.0`–`1.0` | Trace sampling ratio |

## Makefile commands

```bash
make up              # Start full stack
make down            # Stop stack
make seed            # Seed catalog products
make cache-on        # Enable Redis cache
make cache-off       # Disable cache (DummyCache)
make broker-redis    # Switch Celery broker to Redis
make broker-rabbitmq # Switch Celery broker to RabbitMQ
make load-read       # Locust read-heavy traffic
make load-write      # Locust write-heavy traffic
make load-mixed      # Locust mixed traffic
make load-headless   # Headless load test with HTML report
make grafana         # Print Grafana URL
make otel-on         # Enable OpenTelemetry
make otel-off        # Disable OpenTelemetry
```

## API endpoints

- `GET /health/live/` — Liveness probe
- `GET /health/ready/` — Readiness (DB, cache, broker)
- `GET /api/v1/system/config/` — Effective runtime config
- `GET /api/v1/catalog/products/` — Paginated product list
- `GET /api/v1/catalog/products/{id}/` — Product detail
- `POST /api/v1/orders/` — Sync order creation
- `POST /api/v1/orders/async/` — Async order via Celery
- `GET /api/v1/orders/tasks/{task_id}/` — Poll async task status

See [EXPERIMENTS.md](EXPERIMENTS.md) for step-by-step optimization scenarios.

## Ports

| Service | Port |
|---------|------|
| Nginx (API) | 80 |
| Grafana | 3000 |
| Prometheus | 9090 |
| Loki | 3100 |
| RabbitMQ Management | 15672 |
| PostgreSQL | 5432 (internal) |

## Switching broker or cache

Changing `CELERY_BROKER_BACKEND` or `CACHE_ENABLED` requires restarting affected services:

```bash
make broker-rabbitmq   # updates .env and restarts api + worker + beat
make cache-off         # updates .env and restarts api
```

Verify with `curl http://localhost/api/v1/system/config/`.

# Optimization Experiments

Step-by-step scenarios for the Load Lab. Record baseline metrics before each change (Locust RPS, p95 latency, nginx access log `urt=` values, `docker stats`).

## Prerequisites

```bash
cp .env.example .env
make up
make seed
make config    # verify runtime settings
```

---

## Experiment 1: Baseline (no cache)

**Goal:** Establish baseline read/write performance.

```bash
make cache-off
make load-headless   # or: make load-mixed with Locust UI
```

**Record:** RPS, p95 response time, CPU/memory from `docker stats`.

**Expected:** Catalog list endpoints hit PostgreSQL on every request; higher DB CPU.

---

## Experiment 2: Enable Redis cache

**Goal:** Measure cache impact on read-heavy traffic.

```bash
make cache-on
make load-read
# Run same Locust profile as Experiment 1
make load-headless
```

**Compare:** Catalog list latency should drop significantly after warm-up (first page still cold).

**Verify:** `curl http://localhost/api/v1/system/config/` shows `"cache_enabled": true`.

---

## Experiment 3: Celery broker swap (Redis vs RabbitMQ)

**Goal:** Compare message broker behavior under async write load.

```bash
make broker-redis
make load-async

# Switch broker (restarts api + worker + beat)
make broker-rabbitmq
make load-async
```

**Compare:** Task queue latency (time from POST `/orders/async/` to task `SUCCESS`), worker CPU, broker container stats.

**Note:** Result backend stays on Redis DB 2 in both cases.

---

## Experiment 4: Worker scaling

**Goal:** Find saturation point for API and Celery workers.

Edit `.env`:

```env
UVICORN_WORKERS=2    # try 2, 4, 8
CELERY_CONCURRENCY=2 # try 2, 4, 8
```

```bash
docker compose up -d api worker
make load-mixed
```

**Observe:** At low workers, RPS plateaus; at high workers, DB or broker may become bottleneck.

---

## Experiment 5: Cache failure mode

**Goal:** Test graceful degradation when Redis dies.

```bash
make cache-on
make load-read          # confirm cache working
docker compose stop redis
make load-read          # API should stay up (IGNORE_EXCEPTIONS=True)
docker compose start redis
```

**Check:** `/health/ready/` cache check fails while API still serves (slower, from DB).

---

## Experiment 6: Database connection pooling

**Goal:** Tune connection reuse under write load.

Edit `.env`:

```env
DATABASE_CONN_MAX_AGE=0   # no pooling
# then try 60, 300
```

```bash
docker compose up -d api worker
make load-write
```

**Compare:** Connection overhead at `CONN_MAX_AGE=0` vs pooled connections.

---

## Experiment 7: Nginx rate limiting

**Goal:** Protect backend with edge rate limits.

Edit `nginx/nginx.conf` — uncomment `limit_req_zone` and `limit_req` lines (set rate to e.g. `10r/s`).

```bash
docker compose up -d nginx
make load-mixed
```

**Observe:** 429 responses in nginx access log; backend RPS capped.

---

## Experiment 8: Sync vs async orders

**Goal:** Compare API latency for heavy order processing.

Edit `.env`:

```env
CELERY_TASK_SLEEP_SECONDS=2.0
```

```bash
make load-write    # sync — clients wait for full processing
make load-async    # async — clients get 202 quickly, worker does work
```

**Compare:** p95 for sync POST vs async POST; worker queue depth under async load.

---

## Experiment 9: Cache warm-up (Celery beat)

**Goal:** Cold start vs warm cache.

```bash
make cache-on
docker compose exec api python manage.py shell -c "from django.core.cache import cache; cache.clear()"
make load-read   # cold

# Wait for beat task (every 5 min) or trigger manually:
docker compose exec worker celery -A config call apps.orders.tasks.warm_catalog_cache
make load-read   # warm
```

---

## Experiment 10: Observe cache on/off in Grafana

**Goal:** Correlate optimization changes with traces, metrics, and logs in Grafana.

```bash
make grafana    # open http://localhost:3000 → LoadLab Overview dashboard
make cache-off
make load-read  # or make load-headless
# note p95 in Prometheus panel + DB-heavy traces in Tempo

make cache-on
make load-read  # same test
# compare: lower p95, shorter DB spans in traces, fewer slow_request logs in Loki
```

**LogQL during test:**
```logql
{service="api"} |= "slow_request" | json
```

**Tempo:** search `service.name="loadlab-api"` and compare span duration for catalog endpoints.

**Compare:** Locust p95 + Grafana Prometheus panel + Loki slow_request count + Tempo DB child span duration.

---

## Experiment 11: Database index impact

**Goal:** Observe how indexes affect query plans, scan rates, and read latency.

**Prerequisites:** If Postgres was created before `pg_stat_statements` support was added, restart Postgres and enable the extension once:

```bash
docker compose up -d postgres
make db-init-stats
```

```bash
make cache-off
make db-reset-stats
make db-explain          # baseline — note Index Scan on category_list
make grafana             # open LoadLab → LoadLab Database dashboard
```

Drop category indexes for comparison (composite + single-column category):

```bash
make db-index-list           # see registry, groups, and live index names
make db-index-experiment-off # drops category-read group with verification
make db-explain              # expect Seq Scan on category_list
make load-read               # watch sequential scan rate rise in Grafana
```

Restore indexes (uses saved indexdef or registry DDL — not migrate):

```bash
make db-index-experiment-on
make db-explain
make load-read
```

Single-index toggle:

```bash
make db-drop-index INDEX=catalog_pro_categor_da8cc9_idx
make db-add-index INDEX=catalog_pro_categor_da8cc9_idx
```

**CLI helpers:**

| Command | Purpose |
|---------|---------|
| `make db-explain` | EXPLAIN (ANALYZE, BUFFERS) for lab query scenarios |
| `make db-indexes` | List indexes on catalog/orders tables |
| `make db-index-list` | Registry, groups, saved DDL, and live indexes |
| `make db-drop-index` / `make db-add-index` | Toggle one index with verification |
| `make db-index-experiment-off` / `-on` | Toggle category-read index group |
| `make db-index-stats` | pg_stat_user_indexes vs table seq_scan counts |
| `make db-reset-stats` | Reset pg_stat counters between runs |

**Compare:** `make db-explain` scan type (Seq vs Index) + Grafana Database dashboard seq_scan rate + Locust p95 with cache off.

---

## Metrics cheat sheet

| Source | What to watch |
|--------|---------------|
| Locust UI / HTML report | RPS, p50/p95/p99, failure rate |
| `docker stats` | CPU/memory per container |
| `docker compose logs nginx` | `urt=` upstream response time |
| `docker compose logs api` | `slow_request` JSON logs |
| `/api/v1/system/config/` | Effective toggles during test |
| RabbitMQ UI (:15672) | Queue depth, publish/deliver rates |
| Grafana (:3000) | Dashboards, Loki logs, Tempo traces, Prom metrics |
| Grafana → LoadLab Database | Index scans, seq scans, pg_stat_statements |
| Prometheus (:9090) | Raw OTel-derived metrics |
| `make db-explain` | EXPLAIN plans for lab ORM queries |
| `make db-index-list` | Toggleable index registry and live Postgres indexes |
| `make db-index-experiment-off` / `-on` | Drop/restore category-read index group |

---

## Suggested learning path

1. Baseline → Cache on/off (Experiments 1–2)
2. Sync vs async orders (Experiment 8)
3. Broker swap (Experiment 3)
4. Worker scaling (Experiment 4)
5. Failure modes (Experiment 5)
6. Edge protection (Experiment 7)
7. Grafana observability (Experiment 10)
8. Database indexes (Experiment 11)

After mastering these, consider splitting `catalog` and `orders` into separate microservice containers as a follow-up exercise.

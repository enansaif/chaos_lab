# Observability Guide

The Load Lab includes an always-on observability stack for traces, metrics, and logs.

## Stack

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards, Explore (logs + traces) |
| Loki | http://localhost:3100 | Log storage (API internal) |
| Tempo | http://localhost:3200 | Trace storage (API internal) |
| Prometheus | http://localhost:9090 | Metrics storage |
| postgres_exporter | internal :9187 | Postgres index/scan metrics |
| OTel Collector | :4317 / :4318 | Receives telemetry from Django/Celery |

Default Grafana login: `admin` / `admin` (override via `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` in `.env`).

## Data flow

```
Django/Celery  ──OTLP──►  OTel Collector  ──►  Tempo (traces)
                                              └──►  Prometheus (metrics)

Container stdout  ──►  Grafana Alloy  ──►  Loki (logs)

PostgreSQL  ──►  postgres_exporter  ──►  Prometheus  ──►  Grafana (Database dashboard)
```

Logs include `trace_id` and `span_id` when OpenTelemetry is enabled, enabling log-to-trace correlation in Grafana.

## Quick start

```bash
make up
make grafana          # print URLs
curl http://localhost/api/v1/catalog/products/   # generate a trace
```

Open Grafana → **Dashboards** → **LoadLab** → **LoadLab Overview** or **LoadLab Database**.

Or use **Explore**:
- Datasource **Loki** for logs
- Datasource **Tempo** for traces
- Datasource **Prometheus** for metrics

## Example LogQL queries

**Slow requests during load test:**
```logql
{service="api"} |= "slow_request" | json
```

**All API request logs:**
```logql
{service="api"} |= "request_completed"
```

**Celery task completions:**
```logql
{service="worker"} |= "succeeded"
```

**Logs with trace correlation:**
```logql
{service="api"} | json | trace_id != ""
```

Click **TraceID** derived field in a log line to jump to Tempo.

## Example PromQL queries

**HTTP request rate (OTel metrics via collector):**
```promql
sum(rate(http_server_duration_milliseconds_count[1m]))
```

**HTTP p95 latency:**
```promql
histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket[5m])) by (le))
```

**Index scans per second:**
```promql
rate(pg_stat_user_indexes_idx_scan{datname="loadlab"}[1m])
```

**Sequential scans per second:**
```promql
rate(pg_stat_user_tables_seq_scan{datname="loadlab"}[1m])
```

## Database index observability

On-demand query plans and index stats via the `db_observe` management command:

```bash
make db-explain       # EXPLAIN (ANALYZE, BUFFERS) for lab ORM scenarios
make db-indexes       # list indexes on catalog/orders tables
make db-index-list    # registry, groups, and live Postgres indexes
make db-index-experiment-off  # drop category-read indexes (verified)
make db-index-experiment-on   # restore category-read indexes (verified)
make db-index-stats   # pg_stat_user_indexes vs seq_scan counts
make db-reset-stats   # reset counters between experiment runs
make db-init-stats    # enable pg_stat_statements on existing Postgres volumes
```

Continuous metrics appear on the **LoadLab Database** Grafana dashboard (index scans, sequential scans, pg_stat_statements). See [EXPERIMENTS.md](EXPERIMENTS.md) Experiment 11.

## Load test workflow

1. Open Grafana **LoadLab Overview** dashboard
2. Run `make load-mixed` (or `make load-headless`)
3. Watch:
   - Prometheus panels for RPS and p95
   - Loki panels for slow requests and Celery tasks
4. In Tempo Explore, search `service.name=loadlab-api` for slow traces
5. Click a trace → view DB/Redis spans → jump to correlated logs

## Toggles

```bash
make otel-off    # disable app-side instrumentation (stack still runs)
make otel-on     # re-enable
make config      # verify otel_enabled in API response
```

When `OTEL_ENABLED=false`, the API still runs but no traces/metrics are exported. Loki still collects stdout logs via Alloy.

## Makefile shortcuts

| Command | Action |
|---------|--------|
| `make grafana` | Print Grafana URL |
| `make prometheus` | Print Prometheus URL |
| `make obs-logs` | Print example LogQL queries |
| `make otel-on` / `make otel-off` | Toggle instrumentation |
| `make db-explain` | EXPLAIN lab ORM queries |
| `make db-index-list` | Index registry and live Postgres indexes |
| `make db-index-experiment-off` / `-on` | Drop/restore category-read index group |
| `make db-indexes` | List Postgres indexes |
| `make db-index-stats` | Index vs sequential scan stats |
| `make db-reset-stats` | Reset pg_stat counters |
| `make db-init-stats` | Enable pg_stat_statements extension |

See [EXPERIMENTS.md](EXPERIMENTS.md) Experiment 10 for a cache on/off observability exercise.
See Experiment 11 for database index impact.

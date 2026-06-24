# Observability Guide

The Load Lab includes an always-on observability stack for traces, metrics, and logs.

## Stack

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards, Explore (logs + traces) |
| Loki | http://localhost:3100 | Log storage (API internal) |
| Tempo | http://localhost:3200 | Trace storage (API internal) |
| Prometheus | http://localhost:9090 | Metrics storage |
| OTel Collector | :4317 / :4318 | Receives telemetry from Django/Celery |

Default Grafana login: `admin` / `admin` (override via `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` in `.env`).

## Data flow

```
Django/Celery  ──OTLP──►  OTel Collector  ──►  Tempo (traces)
                                              └──►  Prometheus (metrics)

Container stdout  ──►  Grafana Alloy  ──►  Loki (logs)
```

Logs include `trace_id` and `span_id` when OpenTelemetry is enabled, enabling log-to-trace correlation in Grafana.

## Quick start

```bash
make up
make grafana          # print URLs
curl http://localhost/api/v1/catalog/products/   # generate a trace
```

Open Grafana → **Dashboards** → **LoadLab** → **LoadLab Overview**.

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

See [EXPERIMENTS.md](EXPERIMENTS.md) Experiment 10 for a cache on/off observability exercise.

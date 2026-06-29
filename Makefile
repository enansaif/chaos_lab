.PHONY: up down build logs seed cache-on cache-off broker-redis broker-rabbitmq \
        load-read load-write load-async load-mixed load-headless load-docker shell migrate test \
        config health otel-on otel-off grafana prometheus obs-logs \
        db-explain db-indexes db-index-stats db-reset-stats db-init-stats \
        db-index-list db-drop-index db-add-index db-drop-index-group db-add-index-group \
        db-index-experiment-off db-index-experiment-on

COMPOSE = docker compose
ENV_FILE = .env
INDEX ?= catalog_pro_categor_da8cc9_idx
INDEX_GROUP ?= category-read
LAB_INDEX_SCRIPT = ./scripts/lab_indexes.sh

# Start the full Docker stack in the background (builds images if needed).
up: $(ENV_FILE)
	$(COMPOSE) up -d --build

# Stop and remove all running containers (keeps volumes).
down:
	$(COMPOSE) down

# Build Docker images without starting containers.
build:
	$(COMPOSE) build

# Follow logs from api, worker, and nginx services.
logs:
	$(COMPOSE) logs -f api worker nginx

# Create .env from .env.example when missing.
$(ENV_FILE):
	cp .env.example $(ENV_FILE)

# Truncate and re-seed the catalog with sample products for load tests.
seed:
	$(COMPOSE) exec api python manage.py seed_catalog --flush

# Apply Django database migrations.
migrate:
	$(COMPOSE) exec api python manage.py migrate

# Run the test suite locally (uses .venv, disables OpenTelemetry).
test:
	cd src && OTEL_ENABLED=false ../.venv/bin/python -m pytest -v

# Run the test suite inside the api container with in-memory Celery.
test-docker:
	$(COMPOSE) exec \
		-e DJANGO_SETTINGS_MODULE=config.test_settings \
		-e OTEL_ENABLED=false \
		-e CELERY_BROKER_URL=memory:// \
		-e CELERY_RESULT_BACKEND=cache+memory:// \
		-e CELERY_BROKER_BACKEND=memory \
		api pytest -v

# Open an interactive Django shell in the api container.
shell:
	$(COMPOSE) exec api python manage.py shell

# Print effective runtime configuration from the API.
config:
	curl -s http://localhost/api/v1/system/config/ | python3 -m json.tool

# Print readiness probe status (DB, cache, broker checks).
health:
	curl -s http://localhost/health/ready/ | python3 -m json.tool

# Enable Redis caching and restart the api service.
cache-on: $(ENV_FILE)
	@sed -i 's/^CACHE_ENABLED=.*/CACHE_ENABLED=true/' $(ENV_FILE)
	$(COMPOSE) up -d api
	@echo "Cache enabled. Verify: make config"

# Disable caching (DummyCache) and restart the api service.
cache-off: $(ENV_FILE)
	@sed -i 's/^CACHE_ENABLED=.*/CACHE_ENABLED=false/' $(ENV_FILE)
	$(COMPOSE) up -d api
	@echo "Cache disabled. Verify: make config"

# Switch Celery broker to Redis and restart api, worker, and beat.
broker-redis: $(ENV_FILE)
	@sed -i 's/^CELERY_BROKER_BACKEND=.*/CELERY_BROKER_BACKEND=redis/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "Celery broker set to Redis. Verify: make config"

# Switch Celery broker to RabbitMQ and restart api, worker, and beat.
broker-rabbitmq: $(ENV_FILE)
	@sed -i 's/^CELERY_BROKER_BACKEND=.*/CELERY_BROKER_BACKEND=rabbitmq/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "Celery broker set to RabbitMQ. Verify: make config"

# Enable OpenTelemetry instrumentation and restart api, worker, and beat.
otel-on: $(ENV_FILE)
	@sed -i 's/^OTEL_ENABLED=.*/OTEL_ENABLED=true/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "OpenTelemetry enabled. Verify: make config"

# Disable OpenTelemetry instrumentation and restart api, worker, and beat.
otel-off: $(ENV_FILE)
	@sed -i 's/^OTEL_ENABLED=.*/OTEL_ENABLED=false/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "OpenTelemetry disabled. Verify: make config"

# Print Grafana URL and available dashboard names.
grafana:
	@echo "Grafana:  http://localhost:3000  (admin/admin by default)"
	@echo "Dashboards: LoadLab → LoadLab Overview, LoadLab Database"

# Print Prometheus metrics UI URL.
prometheus:
	@echo "Prometheus: http://localhost:9090"

# Run EXPLAIN (ANALYZE, BUFFERS) on lab ORM query scenarios.
db-explain:
	$(COMPOSE) exec api python manage.py db_observe --explain

# List indexes on catalog and orders tables.
db-indexes:
	$(COMPOSE) exec api python manage.py db_observe --list-indexes

# Show index scan vs sequential scan stats from pg_stat views.
db-index-stats:
	$(COMPOSE) exec api python manage.py db_observe --index-stats

# Reset pg_stat_statements and pg_stat counters between experiment runs.
db-reset-stats:
	$(COMPOSE) exec api python manage.py db_observe --reset-stats

# Enable pg_stat_statements extension on existing Postgres volumes.
db-init-stats:
	$(COMPOSE) exec postgres psql -U loadlab -d loadlab -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# List toggleable index registry, groups, and live Postgres indexes.
db-index-list:
	COMPOSE="$(COMPOSE)" $(LAB_INDEX_SCRIPT) list

# Drop one Postgres index by name (INDEX=...) with post-drop verification.
db-drop-index:
	COMPOSE="$(COMPOSE)" $(LAB_INDEX_SCRIPT) drop $(INDEX)

# Recreate one Postgres index by name (INDEX=...) with post-create verification.
db-add-index:
	COMPOSE="$(COMPOSE)" $(LAB_INDEX_SCRIPT) add $(INDEX)

# Drop all indexes in a group (INDEX_GROUP=..., default category-read).
db-drop-index-group:
	COMPOSE="$(COMPOSE)" $(LAB_INDEX_SCRIPT) drop-group $(INDEX_GROUP)

# Recreate all indexes in a group (INDEX_GROUP=..., default category-read).
db-add-index-group:
	COMPOSE="$(COMPOSE)" $(LAB_INDEX_SCRIPT) add-group $(INDEX_GROUP)

# Drop category-read indexes for Experiment 11 (composite + single-column category).
db-index-experiment-off:
	$(MAKE) db-drop-index-group INDEX_GROUP=category-read
	@echo "Next: make cache-off && make db-explain && make load-read"

# Restore category-read indexes for Experiment 11.
db-index-experiment-on:
	$(MAKE) db-add-index-group INDEX_GROUP=category-read
	@echo "Next: make db-explain && make load-read"

# Print example LogQL queries for Grafana Explore (Loki).
obs-logs:
	@echo "Grafana Explore → Loki. Example queries:"
	@echo '  {service="api"} |= "slow_request"'
	@echo '  {service="worker"} |= "succeeded"'
	@echo '  {service="api"} | json | trace_id != ""'

LOCUST = .venv/bin/locust
LOCUST_HOST ?= http://localhost
LOCUST_USERS ?= $(shell grep '^LOCUST_USERS=' $(ENV_FILE) 2>/dev/null | cut -d= -f2- | tr -d ' ' || echo 50)
LOCUST_SPAWN_RATE ?= $(shell grep '^LOCUST_SPAWN_RATE=' $(ENV_FILE) 2>/dev/null | cut -d= -f2- | tr -d ' ' || echo 10)
LOCUST_RUN_TIME ?= $(shell grep '^LOCUST_RUN_TIME=' $(ENV_FILE) 2>/dev/null | cut -d= -f2- | tr -d ' ' || echo 5m)
SEED_PRODUCT_COUNT ?= $(shell grep '^SEED_PRODUCT_COUNT=' $(ENV_FILE) 2>/dev/null | cut -d= -f2- | tr -d ' ' || echo 10000)
LOCUST_ENV = SEED_PRODUCT_COUNT=$(SEED_PRODUCT_COUNT)

# Run Locust read-heavy traffic (catalog list/detail) with interactive UI.
load-read:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) CatalogReader

# Run Locust write-heavy traffic (sync order creation) with interactive UI.
load-write:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) OrderWriter

# Run Locust async order traffic (Celery pipeline) with interactive UI.
load-async:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) AsyncOrderWriter

# Run Locust mixed read/write/async traffic with interactive UI.
load-mixed:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) MixedTraffic

# Run headless mixed load test and save HTML report to reports/.
load-headless:
	mkdir -p reports
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) MixedTraffic \
		--headless -u $(LOCUST_USERS) -r $(LOCUST_SPAWN_RATE) \
		--run-time $(LOCUST_RUN_TIME) \
		--html reports/load-report.html
	@echo "Report saved to reports/load-report.html"

# Run headless mixed load test inside Docker (no local Locust install needed).
load-docker:
	mkdir -p reports
	$(COMPOSE) --profile load run --rm locust \
		--headless -u $(LOCUST_USERS) -r $(LOCUST_SPAWN_RATE) \
		--run-time $(LOCUST_RUN_TIME) MixedTraffic \
		--html /app/reports/load-report.html

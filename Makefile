.PHONY: up down build logs seed cache-on cache-off broker-redis broker-rabbitmq \
        load-read load-write load-async load-mixed load-headless load-docker shell migrate test \
        config health otel-on otel-off grafana prometheus obs-logs

COMPOSE = docker compose
ENV_FILE = .env

up: $(ENV_FILE)
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f api worker nginx

$(ENV_FILE):
	cp .env.example $(ENV_FILE)

seed:
	$(COMPOSE) exec api python manage.py seed_catalog --flush

migrate:
	$(COMPOSE) exec api python manage.py migrate

test:
	cd src && OTEL_ENABLED=false ../.venv/bin/python -m pytest -v

test-docker:
	$(COMPOSE) exec \
		-e DJANGO_SETTINGS_MODULE=config.test_settings \
		-e OTEL_ENABLED=false \
		-e CELERY_BROKER_URL=memory:// \
		-e CELERY_RESULT_BACKEND=cache+memory:// \
		-e CELERY_BROKER_BACKEND=memory \
		api pytest -v

shell:
	$(COMPOSE) exec api python manage.py shell

config:
	curl -s http://localhost/api/v1/system/config/ | python3 -m json.tool

health:
	curl -s http://localhost/health/ready/ | python3 -m json.tool

cache-on: $(ENV_FILE)
	@sed -i 's/^CACHE_ENABLED=.*/CACHE_ENABLED=true/' $(ENV_FILE)
	$(COMPOSE) up -d api
	@echo "Cache enabled. Verify: make config"

cache-off: $(ENV_FILE)
	@sed -i 's/^CACHE_ENABLED=.*/CACHE_ENABLED=false/' $(ENV_FILE)
	$(COMPOSE) up -d api
	@echo "Cache disabled. Verify: make config"

broker-redis: $(ENV_FILE)
	@sed -i 's/^CELERY_BROKER_BACKEND=.*/CELERY_BROKER_BACKEND=redis/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "Celery broker set to Redis. Verify: make config"

broker-rabbitmq: $(ENV_FILE)
	@sed -i 's/^CELERY_BROKER_BACKEND=.*/CELERY_BROKER_BACKEND=rabbitmq/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "Celery broker set to RabbitMQ. Verify: make config"

otel-on: $(ENV_FILE)
	@sed -i 's/^OTEL_ENABLED=.*/OTEL_ENABLED=true/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "OpenTelemetry enabled. Verify: make config"

otel-off: $(ENV_FILE)
	@sed -i 's/^OTEL_ENABLED=.*/OTEL_ENABLED=false/' $(ENV_FILE)
	$(COMPOSE) up -d api worker beat
	@echo "OpenTelemetry disabled. Verify: make config"

grafana:
	@echo "Grafana:  http://localhost:3000  (admin/admin by default)"
	@echo "Dashboard: LoadLab → LoadLab Overview"

prometheus:
	@echo "Prometheus: http://localhost:9090"

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

load-read:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) CatalogReader

load-write:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) OrderWriter

load-async:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) AsyncOrderWriter

load-mixed:
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) MixedTraffic

load-headless:
	mkdir -p reports
	$(LOCUST_ENV) $(LOCUST) -f load_tests/locustfile.py --host $(LOCUST_HOST) MixedTraffic \
		--headless -u $(LOCUST_USERS) -r $(LOCUST_SPAWN_RATE) \
		--run-time $(LOCUST_RUN_TIME) \
		--html reports/load-report.html
	@echo "Report saved to reports/load-report.html"

load-docker:
	mkdir -p reports
	$(COMPOSE) --profile load run --rm locust \
		--headless -u $(LOCUST_USERS) -r $(LOCUST_SPAWN_RATE) \
		--run-time $(LOCUST_RUN_TIME) MixedTraffic \
		--html /app/reports/load-report.html

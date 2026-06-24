# Load Testing

Run against the Nginx front door (port 80):

```bash
make load-read      # CatalogReader — cache impact
make load-write     # OrderWriter — sync writes
make load-async     # AsyncOrderWriter — Celery pipeline
make load-mixed     # MixedTraffic — realistic blend
make load-headless  # Headless with HTML report in reports/
```

Or via Docker (no local Locust install):

```bash
make load-docker
```

## User classes

| Class | Purpose |
|-------|---------|
| `CatalogReader` | 90% list / 10% detail — measures cache hit rate |
| `OrderWriter` | POST sync orders — DB write pressure |
| `AsyncOrderWriter` | POST async + poll task — broker + worker pressure |
| `MixedTraffic` | Weighted blend of all patterns |

## Tips

- Seed data first: `make seed`
- Verify config: `make config`
- Watch logs during tests: `make logs`
- Monitor containers: `docker stats`

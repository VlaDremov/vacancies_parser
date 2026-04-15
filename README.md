`# Hourly ML Vacancies Scraper

Scrapes selected career pages hourly, matches ML-related vacancies, deduplicates notifications for 7 days, and sends Telegram digests.

## Features

- Pluggable parser families: `greenhouse`, `lever`, `workday`, `generic_html`
- HTTP-first fetch with Playwright fallback
- Weighted title/description matching for ML roles
- Geography gate for London, Germany, Netherlands
- PostgreSQL-backed deduplication and run logging
- Hourly Telegram digest with links to new vacancies
- Run overlap protection (file lock) and timeout guard

## Source configuration

Create one file per company in `config/sources` (`.json`, `.yaml`, or `.yml`):

```json
{
  "id": "company_slug",
  "company_name": "Company Name",
  "careers_url": "https://company.com/careers",
  "parser_type": "generic_html",
  "country_hint": "UK",
  "enabled": true,
  "selectors": {
    "job_card": ".job-card",
    "title": ".job-title",
    "link": "a",
    "location": ".job-location",
    "description": ".job-description"
  },
  "pagination": {
    "strategy": "query_param",
    "max_pages": 5,
    "page_param": "page"
  }
}
```

Supported pagination strategies:
- `query_param` (alias: `attrax_page_query`): append `?page=N`
- `offset_limit`: build URLs from `limit` + `offset` (useful for search endpoints like Zalando)

For JSON job endpoints, you can also set `json_job_url_template` (example: `https://jobs.zalando.com/en/jobs/{id}-{slug}`).

## Quick start

1. Copy env file:

```bash
cp .env.example .env
```

2. Add source config files under `config/sources/*.json` or `*.yaml`.

3. Run with Docker:

```bash
docker compose up --build
```

4. Run once manually:

```bash
docker compose run --rm app python -m app.run_once
```

## GitHub Actions

The repo includes [run-scraper.yml](/Users/vlad/Public/Coding_projects/vacancies_parser/.github/workflows/run-scraper.yml) to run the container on GitHub-hosted runners.

It does the following:

- builds the Docker image
- runs the scraper in the container
- connects to an external PostgreSQL database using the `DATABASE_URL` GitHub secret
- works with managed providers such as Neon

Required repository secrets:

- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Important note:

- For this project, the database URL should use the SQLAlchemy `psycopg` driver form: `postgresql+psycopg://...`
- Example Neon shape: `postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require`

## CLI

- `python -m app.run_once`
- `python -m app.backfill --hours 24`
- `python -m app.validate_sources`

## Cron

Use host cron in UTC:

```cron
0 * * * * docker compose run --rm app python -m app.run_once
```

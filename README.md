# Hourly ML Vacancies Scraper

Scrapes career pages and job APIs, matches ML-focused vacancies, deduplicates notifications for 7 days, and sends Telegram digests.

## Features

- Shared parser families for `greenhouse`, `lever`, `workday`, `smartrecruiters`, `teamtailor`, `workable`
- Generic parsers for `generic_html` and `generic_json`
- HTTP-first fetch with Playwright fallback
- Configurable matching profile with weighted positive and negative terms
- Geography and remote-region filtering with per-source overrides
- PostgreSQL or SQLite-backed deduplication and run logging
- Hourly Telegram digest with links to new vacancies
- Source validation CLI for config errors and parser warnings

## Quick Start

1. Create the env file:

```bash
cp .env.example .env
```

2. Install dependencies locally or run with Docker:

```bash
make install
docker compose up --build
```

### Run In Docker

The repo already includes a `Dockerfile` and `docker-compose.yml`.

Build and run one scrape:

```bash
cp .env.example .env
docker compose up --build
```

Run the scraper container directly:

```bash
docker build -t vacancies-parser .
docker run --rm --env-file .env vacancies-parser
```

Notes:

- `.env` is injected at runtime and is not copied into the image.
- The default `.env.example` points `DATABASE_URL` at the `postgres` service from Compose.
- If you want SQLite instead, set `DATABASE_URL=sqlite:////app/vacancies.db` and mount a volume for persistence.

3. Add source config files under `config/sources/*.json`, `*.yaml`, or `*.yml`.

4. Validate sources:

```bash
make validate-sources
```

5. Run one scrape:

```bash
make run-once
```

## Supported Parser Types

- `greenhouse`
- `lever`
- `workday`
- `smartrecruiters`
- `teamtailor`
- `workable`
- `generic_html`
- `generic_json`

Use a shared ATS parser whenever the site is powered by one of those platforms. Use `generic_html` for structured HTML pages and `generic_json` for API-backed listings.

## Source Schema

The preferred source schema is:

```json
{
  "id": "company_slug",
  "company_name": "Company Name",
  "careers_url": "https://company.com/careers",
  "parser_type": "generic_html",
  "country_hint": "Germany",
  "enabled": true,
  "selectors": {
    "job_card": ".job-card",
    "title": ".job-title",
    "link": "a",
    "location": ".job-location",
    "description": ".job-description",
    "posted_at": "time",
    "external_id": "[data-job-id]"
  },
  "pagination": {
    "strategy": "query_param",
    "max_pages": 5,
    "page_param": "page"
  },
  "parser_options": {},
  "matching_profile": {},
  "job_url_template": "https://company.com/jobs/{id}-{slug}"
}
```

### Required Fields

- `id`
- `company_name`
- `careers_url`
- `parser_type`

### Optional Fields

- `country_hint`: used as a fallback location when the parser cannot extract one
- `enabled`: defaults to `true`
- `selectors`: used by `generic_html`
- `pagination`: used by any parser when follow-up pages are needed
- `parser_options`: parser-specific configuration
- `matching_profile`: per-source additions to matching rules
- `job_url_template`: used when a payload has an ID but no direct job URL

### Backward Compatibility

- Existing configs continue to work.
- `json_job_url_template` is still accepted as an alias for `job_url_template`.
- Legacy `pagination` under `extra` is still read, but top-level `pagination` is now preferred.

## Parser-Specific Configuration

### `generic_html`

Use CSS selectors when the job list is visible in the HTML.

Supported selector keys:

- `job_card`
- `title`
- `link`
- `location`
- `description`
- `posted_at`
- `external_id`

### `generic_json`

Use this for API-backed career endpoints.

```json
{
  "id": "example_json_api_company",
  "company_name": "Example JSON API Co",
  "careers_url": "https://api.example.com/jobs",
  "parser_type": "generic_json",
  "parser_options": {
    "jobs_path": "jobs.items",
    "fields": {
      "title": "jobTitle",
      "url": "jobUrl",
      "external_id": "jobId",
      "location": "meta.location",
      "description": "details.summary",
      "posted_at": "meta.publishedAt"
    }
  },
  "pagination": {
    "strategy": "query_param",
    "max_pages": 3,
    "page_param": "page"
  }
}
```

`jobs_path` is a dotted path to the array of jobs. Field mappings are also dotted paths.

If the API does not return job URLs, provide:

```json
{
  "job_url_template": "https://company.com/jobs/{id}-{slug}"
}
```

### Shared ATS Parsers

These parser types usually need only the careers URL:

- `greenhouse`
- `lever`
- `smartrecruiters`
- `teamtailor`
- `workable`
- `workday`

Example:

```json
{
  "id": "example_smartrecruiters_company",
  "company_name": "Example SmartRecruiters Co",
  "careers_url": "https://jobs.smartrecruiters.com/example",
  "parser_type": "smartrecruiters",
  "country_hint": "Germany",
  "enabled": true
}
```

## Pagination

Supported pagination strategies:

- `query_param`: append or replace a page query parameter such as `?page=2`
- `attrax_page_query`: alias for `query_param`
- `offset_limit`: build additional URLs from `offset` and `limit`

Examples:

```json
{
  "pagination": {
    "strategy": "query_param",
    "max_pages": 4,
    "page_param": "page"
  }
}
```

```json
{
  "pagination": {
    "strategy": "offset_limit",
    "max_pages": 3,
    "limit": 15,
    "url_template": "https://api.example.com/jobs?limit={limit}&offset={offset}"
  }
}
```

## Matching

The matcher stays ML-focused by default, but the rules are now configurable.

Global defaults come from `.env`:

- `MATCH_POSITIVE_TERMS_JSON`
- `MATCH_NEGATIVE_TERMS_JSON`
- `MATCH_GEO_TERMS_JSON`
- `MATCH_REMOTE_TERMS_JSON`
- `MATCH_REMOTE_REGION_TERMS_JSON`

Positive and negative term env vars use JSON objects keyed by rule family:

```json
{
  "machine_learning_engineer": {
    "weight": 1.0,
    "terms": ["machine learning engineer", "ml engineer"]
  }
}
```

Per-source overrides are additive. Omitted keys inherit the global defaults.

```json
{
  "matching_profile": {
    "positive_terms": {
      "recommendation_engineer": {
        "weight": 0.9,
        "terms": ["recommendation engineer"]
      }
    },
    "geo_terms": ["madrid", "spain"]
  }
}
```

## CLI

- `make run-once`
- `make backfill`
- `make validate-sources`
- `make test`

Equivalent module entrypoints:

- `python3 -m app.run_once`
- `python3 -m app.backfill --hours 24`
- `python3 -m app.validate_sources`

## Add A New Site

1. Check whether the company uses a supported ATS and prefer that parser type first.
2. If the site exposes a JSON endpoint, use `generic_json`.
3. If the listing is rendered in HTML, use `generic_html` with selectors.
4. Add pagination only if the first page is incomplete.
5. Add a `country_hint` if location extraction is inconsistent.
6. Add `matching_profile` only when the source needs extra ML terms or local geography.
7. Run `make validate-sources`.
8. Run `make test` after adding or changing parser logic.

## Cron

Use host cron in UTC:

```cron
0 * * * * docker compose run --rm app python -m app.run_once
```

CREATE TABLE IF NOT EXISTS sources (
  id VARCHAR(128) PRIMARY KEY,
  company_name VARCHAR(256) NOT NULL,
  careers_url TEXT NOT NULL,
  parser_type VARCHAR(64) NOT NULL,
  country_hint VARCHAR(128),
  selectors JSON NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS vacancies (
  id SERIAL PRIMARY KEY,
  source_id VARCHAR(128) NOT NULL REFERENCES sources(id),
  canonical_hash VARCHAR(64) NOT NULL,
  external_id VARCHAR(256),
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  location TEXT NOT NULL,
  description TEXT NOT NULL,
  posted_at TIMESTAMPTZ,
  first_seen_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT uq_source_canonical UNIQUE (source_id, canonical_hash)
);

CREATE TABLE IF NOT EXISTS matches (
  id SERIAL PRIMARY KEY,
  vacancy_id INTEGER NOT NULL REFERENCES vacancies(id),
  score FLOAT NOT NULL,
  matched_terms_json JSON NOT NULL,
  geo_pass BOOLEAN NOT NULL,
  decision VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY,
  vacancy_id INTEGER NOT NULL REFERENCES vacancies(id),
  channel VARCHAR(64) NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL,
  dedupe_until TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id SERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  status VARCHAR(64) NOT NULL,
  sources_total INTEGER NOT NULL DEFAULT 0,
  jobs_fetched INTEGER NOT NULL DEFAULT 0,
  jobs_matched INTEGER NOT NULL DEFAULT 0,
  jobs_sent INTEGER NOT NULL DEFAULT 0,
  error_summary TEXT
);

-- Tech Rep Scheduler schema (PostgreSQL 14+)
-- Idempotent: safe to run more than once.
-- Run as the app role (techrep) while connected to the techrep database.

BEGIN;

CREATE SCHEMA IF NOT EXISTS techrep AUTHORIZATION CURRENT_USER;
-- Saved on the role so the backend finds the tables without schema-qualifying them.
ALTER ROLE CURRENT_USER SET search_path = techrep, public;
SET LOCAL search_path = techrep, public;

CREATE TABLE IF NOT EXISTS aircraft_types (
    id           SERIAL PRIMARY KEY,
    model_name   VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS mro_locations (
    id            SERIAL PRIMARY KEY,
    facility_name VARCHAR(200) NOT NULL,
    location      VARCHAR(200) NOT NULL,
    airport_code  CHAR(3),
    timezone      VARCHAR(64) NOT NULL DEFAULT 'UTC'
);

CREATE TABLE IF NOT EXISTS tech_reps (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    email      VARCHAR(254) UNIQUE,
    home_base  VARCHAR(200) NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Certifications: which aircraft types each rep is qualified to support.
CREATE TABLE IF NOT EXISTS tech_rep_certifications (
    rep_id           INTEGER NOT NULL REFERENCES tech_reps(id) ON DELETE CASCADE,
    aircraft_type_id INTEGER NOT NULL REFERENCES aircraft_types(id) ON DELETE CASCADE,
    certified_on     DATE,
    expires_on       DATE,
    PRIMARY KEY (rep_id, aircraft_type_id)
);

CREATE TABLE IF NOT EXISTS assignments (
    id               SERIAL PRIMARY KEY,
    rep_id           INTEGER NOT NULL REFERENCES tech_reps(id) ON DELETE RESTRICT,
    mro_id           INTEGER NOT NULL REFERENCES mro_locations(id) ON DELETE RESTRICT,
    aircraft_type_id INTEGER REFERENCES aircraft_types(id) ON DELETE SET NULL,
    start_time       TIMESTAMPTZ NOT NULL,
    end_time         TIMESTAMPTZ NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'proposed'
                     CHECK (status IN ('proposed', 'confirmed', 'in_progress', 'completed', 'cancelled')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_assignments_rep_time ON assignments (rep_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_assignments_mro      ON assignments (mro_id);

COMMIT;

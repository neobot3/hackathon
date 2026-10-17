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

-- ---------------------------------------------------------------------------
-- CBA rules, availability, and MRO demand.
-- Article references are to the WestJet / AMFA CBA in docs/CBA.txt.
-- ---------------------------------------------------------------------------

-- Needed for exclusion constraints that mix "=" on integers with "&&" on ranges.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Article 19-1.08 to 19-1.11. cycle has one character per day: W = work, O = off.
CREATE TABLE IF NOT EXISTS shift_patterns (
    code             VARCHAR(10) PRIMARY KEY,
    description      VARCHAR(200) NOT NULL,
    cycle            VARCHAR(56) NOT NULL CHECK (cycle ~ '^[WO]+$' AND cycle LIKE '%W%'),
    shift_hours      NUMERIC(4, 2) NOT NULL CHECK (shift_hours > 0 AND shift_hours <= 16),
    paid_meal_breaks SMALLINT NOT NULL DEFAULT 0 CHECK (paid_meal_breaks BETWEEN 0 AND 3),
    cba_reference    VARCHAR(20)
);

INSERT INTO shift_patterns (code, description, cycle, shift_hours, paid_meal_breaks, cba_reference) VALUES
    ('5-5-4', '5 on, 5 off, 4 on, 5 off, 5 on, 4 off (Groups I, II, Base Planner)',
              'WWWWWOOOOOWWWWOOOOOWWWWWOOOO', 11.42, 2, '19-1.08'),
    ('5-2',   '5 on, 2 off (Groups IV, V)',            'WWWWWOO',        8.00, 1, '19-1.09'),
    ('7-7',   '7 on, 7 off (Group III)',               'WWWWWWWOOOOOOO', 11.42, 2, '19-1.10'),
    ('4-3',   '4 on, 3 off (Group I, shops)',          'WWWWOOO',        10.00, 2, '19-1.11')
ON CONFLICT (code) DO NOTHING;

-- 19-1.07: 5-5-4 needs a run of consecutive days off in every rolling window (see cba_rules).
ALTER TABLE shift_patterns
    ADD COLUMN IF NOT EXISTS requires_consecutive_days_off BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE shift_patterns SET requires_consecutive_days_off = TRUE WHERE code = '5-5-4';

-- Article 19-5: allowed local start-time windows per pattern and shift.
CREATE TABLE IF NOT EXISTS shift_start_windows (
    shift_pattern_code VARCHAR(10) NOT NULL REFERENCES shift_patterns(code) ON DELETE CASCADE,
    shift_name         VARCHAR(20) NOT NULL CHECK (shift_name IN ('day', 'afternoon', 'night')),
    earliest_start     TIME NOT NULL,
    latest_start       TIME NOT NULL,
    PRIMARY KEY (shift_pattern_code, shift_name),
    CHECK (latest_start >= earliest_start)
);

INSERT INTO shift_start_windows (shift_pattern_code, shift_name, earliest_start, latest_start) VALUES
    ('5-5-4', 'day',       '05:00', '08:00'),
    ('5-5-4', 'afternoon', '13:00', '15:00'),
    ('5-5-4', 'night',     '18:00', '21:00'),
    ('7-7',   'day',       '05:00', '08:00'),
    ('7-7',   'afternoon', '13:00', '15:00'),
    ('7-7',   'night',     '18:00', '21:00'),
    ('5-2',   'day',       '06:00', '09:00')
ON CONFLICT DO NOTHING;

-- Numeric CBA limits the solver reads. One row per agreement; date ranges cannot overlap.
-- effective_to is exclusive; NULL means open-ended.
CREATE TABLE IF NOT EXISTS cba_rules (
    id                              SERIAL PRIMARY KEY,
    name                            VARCHAR(100) NOT NULL UNIQUE,
    effective_from                  DATE NOT NULL,
    effective_to                    DATE,

    -- Hours of work and rest (Article 19)
    min_rest_hours                  NUMERIC(4, 2) NOT NULL DEFAULT 10   CHECK (min_rest_hours > 0),
    min_rest_hours_trade            NUMERIC(4, 2) NOT NULL DEFAULT 8    CHECK (min_rest_hours_trade > 0),
    max_consecutive_scheduled_days  SMALLINT      NOT NULL DEFAULT 7    CHECK (max_consecutive_scheduled_days > 0),
    max_consecutive_worked_days     SMALLINT      NOT NULL DEFAULT 11   CHECK (max_consecutive_worked_days > 0),
    min_hours_off_per_set           NUMERIC(5, 2) NOT NULL DEFAULT 48   CHECK (min_hours_off_per_set >= 0),
    three_days_off_window_days      SMALLINT      NOT NULL DEFAULT 28   CHECK (three_days_off_window_days >= 3),
    avg_weekly_hours                NUMERIC(4, 2) NOT NULL DEFAULT 40   CHECK (avg_weekly_hours > 0),
    averaging_weeks_major_base      SMALLINT      NOT NULL DEFAULT 26   CHECK (averaging_weeks_major_base > 0),
    averaging_weeks_other_base      SMALLINT      NOT NULL DEFAULT 52   CHECK (averaging_weeks_other_base > 0),

    -- Field service away from base (Article 21)
    max_field_duty_hours            NUMERIC(4, 2) NOT NULL DEFAULT 16   CHECK (max_field_duty_hours > 0 AND max_field_duty_hours <= 24),
    post_field_rest_hours           NUMERIC(4, 2) NOT NULL DEFAULT 10   CHECK (post_field_rest_hours >= 0),
    base_coverage_notice_hours      SMALLINT      NOT NULL DEFAULT 48   CHECK (base_coverage_notice_hours >= 0),
    max_vehicle_travel_km           SMALLINT      NOT NULL DEFAULT 550  CHECK (max_vehicle_travel_km > 0),
    field_service_rate              NUMERIC(3, 2) NOT NULL DEFAULT 1.5  CHECK (field_service_rate >= 1),

    -- Overtime and premiums (Articles 15-4, 16-1, 29-3)
    ot_rate_voluntary               NUMERIC(3, 2) NOT NULL DEFAULT 1.5  CHECK (ot_rate_voluntary >= 1),
    ot_voluntary_tier_hours         NUMERIC(4, 2) NOT NULL DEFAULT 8    CHECK (ot_voluntary_tier_hours >= 0),
    ot_rate_voluntary_over_tier     NUMERIC(3, 2) NOT NULL DEFAULT 1.75 CHECK (ot_rate_voluntary_over_tier >= 1),
    ot_rate_mandatory               NUMERIC(3, 2) NOT NULL DEFAULT 2.0  CHECK (ot_rate_mandatory >= 1),
    max_banked_ot_hours             NUMERIC(5, 2) NOT NULL DEFAULT 80   CHECK (max_banked_ot_hours >= 0),
    stat_holiday_rate               NUMERIC(3, 2) NOT NULL DEFAULT 1.5  CHECK (stat_holiday_rate >= 1),

    CHECK (effective_to IS NULL OR effective_to > effective_from),
    CHECK (min_rest_hours_trade <= min_rest_hours),
    CHECK (max_consecutive_scheduled_days <= max_consecutive_worked_days),
    CHECK (ot_rate_voluntary_over_tier >= ot_rate_voluntary),
    CONSTRAINT cba_rules_no_overlap EXCLUDE USING gist (daterange(effective_from, effective_to) WITH &&)
);

-- Defaults above are the values in the 2024-2029 agreement.
INSERT INTO cba_rules (name, effective_from, effective_to)
VALUES ('WestJet / AMFA 2024-2029', DATE '2024-08-01', DATE '2029-07-01')
ON CONFLICT (name) DO NOTHING;

ALTER TABLE cba_rules
    -- 19-1.01: Group I at these bases averages over 26 weeks; everyone else over 52 (19-1.02, 19-1.03).
    ADD COLUMN IF NOT EXISTS major_bases TEXT[] NOT NULL
        DEFAULT '{Calgary,Toronto,Vancouver,Edmonton,YYC,YYZ,YVR,YEG}',
    -- Start of the first averaging period; NULL means effective_from.
    ADD COLUMN IF NOT EXISTS averaging_anchor_date DATE,
    -- 19-1.07: length of the run of days off required in each three_days_off_window_days.
    ADD COLUMN IF NOT EXISTS consecutive_days_off_required SMALLINT NOT NULL DEFAULT 3
        CHECK (consecutive_days_off_required > 0),
    -- 21-3.02: AOG pay starts 2 h before the assignment and ends 2 h after returning home.
    ADD COLUMN IF NOT EXISTS aog_pay_buffer_hours NUMERIC(4, 2) NOT NULL DEFAULT 2
        CHECK (aog_pay_buffer_hours >= 0);

-- Pay periods for the 8 h overtime tier (16-1.04). 24 per year (15-1.01); the solver
-- falls back to the 1st-15th and 16th-end of month when a date has no row here.
CREATE TABLE IF NOT EXISTS pay_periods (
    id         SERIAL PRIMARY KEY,
    start_date DATE NOT NULL,
    -- Exclusive.
    end_date   DATE NOT NULL,
    CHECK (end_date > start_date),
    CONSTRAINT pay_periods_no_overlap EXCLUDE USING gist (daterange(start_date, end_date) WITH &&)
);

-- One-way travel from a home base to an MRO. Counts toward the duty day (21-1.03)
-- and is paid at the field service rate (21-2.02).
CREATE TABLE IF NOT EXISTS travel_times (
    home_base    VARCHAR(200) NOT NULL,
    mro_id       INTEGER NOT NULL REFERENCES mro_locations(id) ON DELETE CASCADE,
    travel_hours NUMERIC(4, 2) NOT NULL CHECK (travel_hours >= 0 AND travel_hours <= 24),
    distance_km  INTEGER CHECK (distance_km >= 0),
    PRIMARY KEY (home_base, mro_id)
);

-- Article 29-3. The CBA does not list the 11 dates, so the scheduler loads them.
CREATE TABLE IF NOT EXISTS statutory_holidays (
    holiday_date DATE PRIMARY KEY,
    name         VARCHAR(100) NOT NULL
);

-- Rep attributes used by CBA rules: seniority (16-1.06, 21-3), shift pattern (19-2),
-- and banked overtime, capped at 80 hours (15-4.02).
ALTER TABLE tech_reps
    ADD COLUMN IF NOT EXISTS classification       VARCHAR(60),
    -- Article 18 group; picks the averaging period in 19-1.01 to 19-1.03.
    ADD COLUMN IF NOT EXISTS cba_group            SMALLINT CHECK (cba_group BETWEEN 1 AND 5),
    ADD COLUMN IF NOT EXISTS union_seniority_date DATE,
    ADD COLUMN IF NOT EXISTS shift_pattern_code   VARCHAR(10)
        REFERENCES shift_patterns(code) ON DELETE RESTRICT,
    -- Date of day 1 of shift_patterns.cycle for this rep.
    ADD COLUMN IF NOT EXISTS shift_cycle_start    DATE,
    ADD COLUMN IF NOT EXISTS banked_ot_hours      NUMERIC(5, 2) NOT NULL DEFAULT 0
        CHECK (banked_ot_hours BETWEEN 0 AND 80);

-- Periods a rep cannot be scheduled (vacation, sick, training, leave).
CREATE TABLE IF NOT EXISTS rep_unavailability (
    id         SERIAL PRIMARY KEY,
    rep_id     INTEGER NOT NULL REFERENCES tech_reps(id) ON DELETE CASCADE,
    reason     VARCHAR(20) NOT NULL
               CHECK (reason IN ('vacation', 'sick', 'training', 'bereavement', 'parental',
                                 'union_leave', 'unpaid_leave', 'jury_duty', 'other')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time   TIMESTAMPTZ NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'approved'
               CHECK (status IN ('requested', 'approved', 'denied', 'cancelled')),
    notes      VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_rep_unavailability_rep_time
    ON rep_unavailability (rep_id, start_time, end_time);

-- Work an MRO needs covered: planned Base Coverage (21-2) or unplanned AOG (21-3).
CREATE TABLE IF NOT EXISTS mro_demands (
    id               SERIAL PRIMARY KEY,
    mro_id           INTEGER NOT NULL REFERENCES mro_locations(id) ON DELETE RESTRICT,
    aircraft_type_id INTEGER NOT NULL REFERENCES aircraft_types(id) ON DELETE RESTRICT,
    demand_type      VARCHAR(20) NOT NULL DEFAULT 'base_coverage'
                     CHECK (demand_type IN ('base_coverage', 'aog')),
    start_time       TIMESTAMPTZ NOT NULL,
    end_time         TIMESTAMPTZ NOT NULL,
    reps_needed      SMALLINT NOT NULL DEFAULT 1 CHECK (reps_needed BETWEEN 1 AND 50),
    -- 1 is the most urgent.
    priority         SMALLINT NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    status           VARCHAR(20) NOT NULL DEFAULT 'open'
                     CHECK (status IN ('open', 'filled', 'cancelled')),
    notes            VARCHAR(500),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_mro_demands_time   ON mro_demands (start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_mro_demands_status ON mro_demands (status);

-- Replies to a solicitation (21-2.06, 21-3.07). Once a demand has replies, reps who did
-- not accept can only be assigned mandatorily, in reverse seniority (16-1.06, 21-2.09, 21-3.08).
CREATE TABLE IF NOT EXISTS demand_responses (
    demand_id    INTEGER NOT NULL REFERENCES mro_demands(id) ON DELETE CASCADE,
    rep_id       INTEGER NOT NULL REFERENCES tech_reps(id) ON DELETE CASCADE,
    response     VARCHAR(10) NOT NULL CHECK (response IN ('accepted', 'declined')),
    responded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (demand_id, rep_id)
);

ALTER TABLE assignments
    ADD COLUMN IF NOT EXISTS demand_id     INTEGER REFERENCES mro_demands(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS overtime_type VARCHAR(10) NOT NULL DEFAULT 'none'
        CHECK (overtime_type IN ('none', 'voluntary', 'mandatory')),
    ADD COLUMN IF NOT EXISTS overtime_hours NUMERIC(5, 2) NOT NULL DEFAULT 0
        CHECK (overtime_hours >= 0),
    -- One way; the rep is away from base this long before start_time and after end_time.
    ADD COLUMN IF NOT EXISTS travel_hours   NUMERIC(4, 2) NOT NULL DEFAULT 0
        CHECK (travel_hours >= 0);

CREATE INDEX IF NOT EXISTS idx_assignments_demand ON assignments (demand_id);

-- A rep cannot hold two live assignments at the same time.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'assignments_no_overlap') THEN
        ALTER TABLE assignments ADD CONSTRAINT assignments_no_overlap
            EXCLUDE USING gist (rep_id WITH =, tstzrange(start_time, end_time) WITH &&)
            WHERE (status <> 'cancelled');
    END IF;
END $$;

COMMIT;

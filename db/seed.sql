-- Sample data transcribed from the Oct-26 and Nov-26 roster spreadsheet.
-- Names and phone numbers are fictitious; 555-01xx numbers are reserved for fiction.
-- tech_reps.id is the sheet's EMP # (lower = more senior). Run after init.sql. Idempotent.

BEGIN;

SET LOCAL search_path = techrep, public;

-- Home bases first so they win the home_base -> MRO lookup over MROs at the same airport.
INSERT INTO mro_locations (facility_name, location, airport_code, timezone)
SELECT v.* FROM (VALUES
    ('YLW', 'Kelowna, BC',          'YLW', 'America/Vancouver'),
    ('YYC', 'Calgary, AB',          'YYC', 'America/Edmonton'),
    ('YYZ', 'Toronto, ON',          'YYZ', 'America/Toronto'),
    ('YEG', 'Edmonton, AB',         'YEG', 'America/Edmonton'),
    ('KFL', 'Kelowna, BC',          'YLW', 'America/Vancouver'),
    ('KFH', 'Hamilton, ON',         'YHM', 'America/Toronto'),
    ('AAR', 'Windsor, ON',          'YQG', 'America/Toronto'),
    ('JDA', 'Sault Ste. Marie, ON', 'YAM', 'America/Toronto'),
    ('FS',  'Jacksonville, FL',     'JAX', 'America/New_York'),
    ('STS', 'Melbourne, FL',        'MLB', 'America/New_York'),
    ('TUS', 'Tucson, AZ',           'TUS', 'America/Phoenix'),
    -- Not in the sheet legend: location and timezone are placeholders.
    ('IAC', 'TBD',                  NULL,  'America/Edmonton')
) AS v(facility_name, location, airport_code, timezone)
WHERE NOT EXISTS (SELECT 1 FROM mro_locations m WHERE m.facility_name = v.facility_name);

-- Kelowna covers Kelowna, Toronto covers the east, Calgary covers the rest.
UPDATE mro_locations m
SET covering_base = v.base
FROM (VALUES
    ('YLW', 'YLW'), ('KFL', 'YLW'),
    ('YYZ', 'YYZ'), ('KFH', 'YYZ'), ('AAR', 'YYZ'), ('JDA', 'YYZ'), ('FS', 'YYZ'),
    ('STS', 'YYZ'),
    ('YYC', 'YYC'), ('YEG', 'YYC'), ('TUS', 'YYC'), ('IAC', 'YYC')
) AS v(facility_name, base)
WHERE m.facility_name = v.facility_name AND m.covering_base IS NULL;

-- quals: NG = 737 NG, M = 737 MAX, BCF = 737-800 BCF, Q = Q400, 87 = 787-9.
CREATE TEMP TABLE seed_reps (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR(200),
    phone          VARCHAR(30),
    home_base      VARCHAR(200),
    classification VARCHAR(60),
    quals          TEXT,
    pattern        VARCHAR(10),
    cycle_start    DATE,
    cba_group      SMALLINT
) ON COMMIT DROP;

INSERT INTO seed_reps VALUES
    (18398, 'Owen Kirby',         '(437) 555-0101', 'YYZ', 'RI/TR',    NULL,            '7-7', '2026-10-12', 3),
    (5496,  'Hannah Whitlock',    '(778) 555-0102', 'YLW', 'RI/TR',    NULL,            '7-7', '2026-10-12', 3),
    (839,   'Glen Bauer',         '(250) 555-0103', 'YLW', 'RI/TR',    NULL,            '7-7', '2026-10-05', 3),
    (44766, 'Luc Gagnon',         '(416) 555-0104', 'YYZ', 'RI/TR',    NULL,            '7-7', '2026-10-05', 3),
    (5796,  'Travis Holt',        '(250) 555-0105', 'YLW', 'Lead',     NULL,            '7-7', '2026-10-10', 3),
    (10629, 'Ingrid Solberg',     '(604) 555-0106', 'YLW', 'Lead',     NULL,            '7-7', '2026-10-03', 3),
    (1179,  'Dale Morrison',      '(604) 555-0107', 'YLW', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (32603, 'Kevin Doyle',        '(236) 555-0108', 'YLW', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-08', 3),
    (11620, 'Tara Lindqvist',     '(236) 555-0109', 'YLW', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-01', 3),
    (8517,  'Ryan Castellano',    '(250) 555-0110', 'YLW', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-08', 3),
    (516,   'Gordon Fairweather', '(250) 555-0111', 'YLW', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (23007, 'Neil Haverford',     '(250) 555-0112', 'YLW', 'Tech Rep', 'NG/M/BCF/Q',    '7-7', '2026-10-08', 3),
    (45993, 'Eli Northcott',      '(587) 555-0113', 'YLW', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-01', 3),
    (16184, 'Brent Calloway',     '(403) 555-0114', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-08', 3),
    (16205, 'Henrik Dahl',        '(587) 555-0115', 'YYC', 'Tech Rep', 'NG/M/BCF/87',   '7-7', '2026-10-08', 3),
    (7114,  'Wade Pemberton',     '(587) 555-0116', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (28744, 'Arjun Malhotra',     '(587) 555-0117', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (32614, 'Andre Lavoie',       '(587) 555-0118', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-08', 3),
    (33386, 'Colin Ashby',        '(587) 555-0119', 'YYC', 'Tech Rep', 'NG/M/Q/87',     '7-7', '2026-10-01', 3),
    (19960, 'Nadia Ferreira',     '(587) 555-0120', 'YYC', 'Tech Rep', 'NG/M/Q/87',     '7-7', '2026-10-08', 3),
    (18917, 'Derek Langley',      '(403) 555-0121', 'YYC', 'Tech Rep', 'NG/M/BCF/Q',    '7-7', '2026-10-01', 3),
    (1006,  'Murray Kessler',     '(403) 555-0122', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-08', 3),
    (9519,  'Pierre Beaulieu',    '(403) 555-0123', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (19302, 'Ian Fraser',         '(587) 555-0124', 'YYC', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-08', 3),
    (19685, 'Mateo Alvarez',      '(403) 555-0125', 'YYC', 'Tech Rep', 'NG/M/Q/87',     '7-7', '2026-10-01', 3),
    (39106, 'Samir Haddad',       '(403) 555-0126', 'YYC', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-08', 3),
    (7215,  'Cody Brennan',       '(613) 555-0127', 'YYZ', 'Tech Rep', 'NG/M/BCF/Q/87', '7-7', '2026-10-01', 3),
    (17427, 'Shawn Pelletier',    '(587) 555-0128', 'YYZ', 'Tech Rep', 'NG/M/BCF/87',   '7-7', '2026-10-01', 3),
    (28726, 'Greg Whitfield',     '(416) 555-0129', 'YYZ', 'Tech Rep', 'NG/M/BCF/Q',    '7-7', '2026-10-08', 3),
    (44553, 'Martin Vogel',       '(416) 555-0130', 'YYZ', 'Tech Rep', 'NG/M/Q',        '7-7', '2026-10-01', 3),
    (44564, 'Jordan Ellis',       '(647) 555-0131', 'YYZ', 'Tech Rep', 'NG/M',          '7-7', '2026-10-08', 3),
    -- In Q400 endorsement training Mon-Fri, so no rotation is set.
    (17153, 'Stefan Richter',     '(647) 555-0132', 'YYZ', 'Tech Rep', 'NG/M/BCF/87',   NULL,  NULL,         3),
    (22495, 'Alan Prescott',      '(437) 555-0133', 'YYC', 'Manager',  NULL,            '5-2', '2026-10-05', NULL),
    -- No EMP # on the sheet: placeholder ids above every real one.
    (90001, 'Priya Nair',         NULL,             'YEG', 'International Materials', NULL, '5-2', '2026-10-05', NULL),
    (90002, 'Mei Chen',           NULL,             'YEG', 'International Materials', NULL, '5-2', '2026-10-05', NULL),
    (90003, 'Elena Moretti',      NULL,             'YYZ', 'Coordinator',             NULL, '5-2', '2026-10-05', NULL);

INSERT INTO tech_reps (id, name, phone, home_base, classification, shift_pattern_code,
                       shift_cycle_start, cba_group)
SELECT id, name, phone, home_base, classification, pattern, cycle_start, cba_group
FROM seed_reps
ON CONFLICT (id) DO NOTHING;

-- Explicit ids bypass the sequence; move it past them so new reps get higher (junior) ids.
SELECT setval(pg_get_serial_sequence('tech_reps', 'id'), (SELECT max(id) FROM tech_reps));

INSERT INTO tech_rep_certifications (rep_id, aircraft_type_id)
SELECT r.id, a.id
FROM seed_reps r
CROSS JOIN LATERAL unnest(string_to_array(r.quals, '/')) AS q(code)
JOIN (VALUES
    ('NG',  '737-700 NG'),
    ('NG',  '737-800 NG'),
    ('M',   '737-8 MAX'),
    ('BCF', '737-800 BCF'),
    ('Q',   'Dash 8-400 (Q400)'),
    ('87',  '787-9 Dreamliner')
) AS t(code, model_name) ON t.code = q.code
JOIN aircraft_types a ON a.model_name = t.model_name
ON CONFLICT DO NOTHING;

-- One row per block of sheet cells. An MRO code is an assignment; VAC, AB, OFF and the
-- training codes (TR, FA, 787, Q400, HF, MCM, HT) are unavailability. TVL is not loaded.
CREATE TEMP TABLE seed_schedule (
    rep_id    INTEGER,
    code      VARCHAR(10),
    first_day DATE,
    last_day  DATE
) ON COMMIT DROP;

INSERT INTO seed_schedule VALUES
    -- RI/TR
    (839,   'TR',   '2026-10-05', '2026-10-06'),
    (839,   'VAC',  '2026-10-22', '2026-10-25'),
    (839,   'VAC',  '2026-11-04', '2026-11-08'),
    (839,   'VAC',  '2026-11-16', '2026-11-18'),
    (44766, 'VAC',  '2026-10-09', '2026-10-11'),
    (44766, 'VAC',  '2026-10-19', '2026-10-19'),
    (44766, 'VAC',  '2026-11-21', '2026-11-22'),
    (44766, 'VAC',  '2026-11-30', '2026-11-30'),
    (18398, 'VAC',  '2026-10-12', '2026-10-13'),
    (5496,  'VAC',  '2026-11-09', '2026-11-15'),
    -- International Materials and coordinator
    (90001, 'STS',  '2026-10-05', '2026-10-06'),
    (90001, 'FS',   '2026-10-07', '2026-10-09'),
    (90001, 'VAC',  '2026-10-29', '2026-10-30'),
    (90001, 'VAC',  '2026-11-03', '2026-11-03'),
    (90001, 'VAC',  '2026-11-06', '2026-11-06'),
    (90001, 'VAC',  '2026-11-10', '2026-11-10'),
    (90003, 'OFF',  '2026-11-04', '2026-11-04'),
    -- Leads
    (5796,  'AAR',  '2026-10-15', '2026-10-16'),
    (5796,  'VAC',  '2026-10-24', '2026-10-30'),
    (5796,  'FA',   '2026-11-13', '2026-11-13'),
    (10629, 'FA',   '2026-10-22', '2026-10-22'),
    -- Tech reps, rotation starting 2026-10-01
    (1179,  'VAC',  '2026-10-01', '2026-10-07'),
    (1179,  'TUS',  '2026-10-15', '2026-10-21'),
    (1179,  'FA',   '2026-10-22', '2026-10-22'),
    (1179,  'TUS',  '2026-10-29', '2026-11-04'),
    (1179,  'VAC',  '2026-11-12', '2026-11-18'),
    (1179,  'TUS',  '2026-11-26', '2026-11-30'),
    (11620, 'VAC',  '2026-10-01', '2026-10-07'),
    (11620, 'YLW',  '2026-10-15', '2026-10-21'),
    (11620, 'FA',   '2026-10-22', '2026-10-22'),
    (11620, 'YLW',  '2026-10-29', '2026-11-04'),
    (11620, 'YLW',  '2026-11-12', '2026-11-18'),
    (11620, 'YLW',  '2026-11-26', '2026-11-30'),
    (516,   'AB',   '2026-10-01', '2026-10-04'),
    (516,   'YLW',  '2026-10-05', '2026-10-07'),
    (516,   'YLW',  '2026-10-15', '2026-10-21'),
    (516,   'YLW',  '2026-10-29', '2026-11-01'),
    (516,   'HF',   '2026-11-02', '2026-11-02'),
    (516,   'MCM',  '2026-11-03', '2026-11-03'),
    (516,   'HT',   '2026-11-04', '2026-11-04'),
    (516,   'YLW',  '2026-11-12', '2026-11-18'),
    (516,   'YLW',  '2026-11-26', '2026-11-30'),
    (45993, 'KFH',  '2026-10-01', '2026-10-07'),
    (45993, 'KFH',  '2026-10-15', '2026-10-21'),
    (45993, 'KFH',  '2026-10-29', '2026-11-04'),
    (45993, 'KFH',  '2026-11-12', '2026-11-18'),
    (45993, 'KFH',  '2026-11-26', '2026-11-30'),
    (7114,  'VAC',  '2026-10-01', '2026-10-07'),
    (7114,  'TUS',  '2026-10-15', '2026-10-21'),
    (7114,  'FA',   '2026-10-22', '2026-10-22'),
    (7114,  'TUS',  '2026-10-29', '2026-11-04'),
    (7114,  'TUS',  '2026-11-12', '2026-11-18'),
    (7114,  'TUS',  '2026-11-26', '2026-11-30'),
    (28744, 'IAC',  '2026-10-01', '2026-10-07'),
    (28744, 'IAC',  '2026-10-15', '2026-10-21'),
    (28744, 'IAC',  '2026-10-29', '2026-11-04'),
    (28744, 'IAC',  '2026-11-12', '2026-11-18'),
    (28744, 'VAC',  '2026-11-26', '2026-11-29'),
    (28744, 'YLW',  '2026-11-30', '2026-11-30'),
    (33386, 'TUS',  '2026-10-01', '2026-10-07'),
    (33386, 'VAC',  '2026-10-15', '2026-10-21'),
    (33386, 'FS',   '2026-10-29', '2026-11-04'),
    (33386, 'FS',   '2026-11-12', '2026-11-18'),
    (33386, 'KFH',  '2026-11-26', '2026-11-30'),
    (18917, 'KFH',  '2026-11-01', '2026-11-04'),
    (18917, 'VAC',  '2026-11-12', '2026-11-18'),
    (18917, 'YLW',  '2026-11-26', '2026-11-29'),
    (18917, 'VAC',  '2026-11-30', '2026-11-30'),
    (9519,  'JDA',  '2026-11-01', '2026-11-04'),
    (9519,  'FS',   '2026-11-12', '2026-11-18'),
    (9519,  'AAR',  '2026-11-26', '2026-11-30'),
    (19685, 'VAC',  '2026-11-01', '2026-11-04'),
    (19685, 'TUS',  '2026-11-12', '2026-11-18'),
    (19685, 'AAR',  '2026-11-26', '2026-11-30'),
    (7215,  'AAR',  '2026-11-01', '2026-11-04'),
    (7215,  'AAR',  '2026-11-12', '2026-11-18'),
    (7215,  'FS',   '2026-11-26', '2026-11-30'),
    (17427, 'VAC',  '2026-11-01', '2026-11-04'),
    (17427, 'AAR',  '2026-11-12', '2026-11-18'),
    (17427, 'FS',   '2026-11-26', '2026-11-30'),
    (44553, 'VAC',  '2026-11-01', '2026-11-01'),
    (44553, 'KFH',  '2026-11-02', '2026-11-04'),
    (44553, 'JDA',  '2026-11-12', '2026-11-18'),
    (44553, 'FA',   '2026-11-25', '2026-11-25'),
    (44553, 'JDA',  '2026-11-26', '2026-11-30'),
    -- Tech reps, rotation starting 2026-10-08
    (32603, 'TUS',  '2026-10-08', '2026-10-14'),
    (32603, 'YLW',  '2026-10-22', '2026-10-28'),
    (32603, 'YLW',  '2026-11-05', '2026-11-11'),
    (32603, 'FA',   '2026-11-13', '2026-11-13'),
    (32603, 'TUS',  '2026-11-19', '2026-11-25'),
    (8517,  '787',  '2026-10-01', '2026-10-02'),
    (8517,  '787',  '2026-10-05', '2026-10-09'),
    (8517,  '787',  '2026-10-12', '2026-10-16'),
    (8517,  '787',  '2026-10-19', '2026-10-21'),
    (8517,  'YLW',  '2026-10-22', '2026-10-28'),
    (8517,  'YLW',  '2026-11-05', '2026-11-11'),
    (8517,  'FA',   '2026-11-13', '2026-11-13'),
    (8517,  'YLW',  '2026-11-19', '2026-11-25'),
    (23007, 'YLW',  '2026-10-08', '2026-10-14'),
    (23007, 'KFH',  '2026-10-22', '2026-10-28'),
    (23007, 'KFH',  '2026-11-05', '2026-11-11'),
    (23007, 'KFH',  '2026-11-19', '2026-11-25'),
    (16184, 'IAC',  '2026-10-08', '2026-10-14'),
    (16184, 'IAC',  '2026-10-22', '2026-10-28'),
    (16184, 'IAC',  '2026-11-05', '2026-11-11'),
    (16184, 'IAC',  '2026-11-19', '2026-11-25'),
    (16205, 'YLW',  '2026-10-08', '2026-10-09'),
    (16205, 'VAC',  '2026-10-10', '2026-10-14'),
    (16205, 'TUS',  '2026-10-22', '2026-10-28'),
    (16205, 'VAC',  '2026-11-05', '2026-11-06'),
    (16205, 'AB',   '2026-11-07', '2026-11-07'),
    (16205, 'VAC',  '2026-11-08', '2026-11-11'),
    (16205, 'FS',   '2026-11-19', '2026-11-25'),
    (32614, 'KFH',  '2026-10-08', '2026-10-14'),
    (32614, 'FS',   '2026-10-22', '2026-10-28'),
    (32614, 'FS',   '2026-11-05', '2026-11-11'),
    (32614, 'AAR',  '2026-11-19', '2026-11-25'),
    (19960, 'TUS',  '2026-11-05', '2026-11-11'),
    (19960, 'VAC',  '2026-11-19', '2026-11-25'),
    (1006,  'JDA',  '2026-11-05', '2026-11-11'),
    (1006,  'FS',   '2026-11-19', '2026-11-25'),
    (19302, 'TUS',  '2026-11-05', '2026-11-11'),
    (19302, 'TUS',  '2026-11-19', '2026-11-25'),
    (39106, 'VAC',  '2026-11-05', '2026-11-11'),
    (39106, 'VAC',  '2026-11-19', '2026-11-25'),
    (28726, 'VAC',  '2026-11-05', '2026-11-10'),
    (28726, 'AB',   '2026-11-11', '2026-11-11'),
    (28726, 'JDA',  '2026-11-19', '2026-11-25'),
    (44564, 'AAR',  '2026-11-05', '2026-11-10'),
    (44564, 'AB',   '2026-11-11', '2026-11-11'),
    (44564, 'VAC',  '2026-11-19', '2026-11-25'),
    -- Q400 endorsement training
    (17153, 'Q400', '2026-11-02', '2026-11-06'),
    (17153, 'Q400', '2026-11-09', '2026-11-13'),
    (17153, 'Q400', '2026-11-16', '2026-11-20'),
    (17153, 'Q400', '2026-11-23', '2026-11-27');

-- One 11.42 h day shift (7-7 pattern) per day, in the MRO's local time.
INSERT INTO assignments (rep_id, mro_id, start_time, end_time, status)
SELECT s.rep_id, m.id,
       (d::date + TIME '07:00') AT TIME ZONE m.timezone,
       (d::date + TIME '18:25') AT TIME ZONE m.timezone,
       'confirmed'
FROM seed_schedule s
JOIN mro_locations m ON m.facility_name = s.code
CROSS JOIN LATERAL generate_series(s.first_day, s.last_day, INTERVAL '1 day') AS d
ON CONFLICT DO NOTHING;

-- Whole local days at the rep's home base.
INSERT INTO rep_unavailability (rep_id, reason, start_time, end_time, status, notes)
SELECT s.rep_id,
       CASE s.code WHEN 'VAC' THEN 'vacation' WHEN 'AB' THEN 'other' WHEN 'OFF' THEN 'other'
                   ELSE 'training' END,
       s.first_day::timestamp AT TIME ZONE b.timezone,
       (s.last_day + 1)::timestamp AT TIME ZONE b.timezone,
       'approved',
       'Roster code ' || s.code
FROM seed_schedule s
JOIN tech_reps r ON r.id = s.rep_id
JOIN mro_locations b ON b.facility_name = r.home_base
WHERE s.code IN ('VAC', 'AB', 'OFF', 'TR', 'FA', '787', 'Q400', 'HF', 'MCM', 'HT')
  AND NOT EXISTS (
      SELECT 1 FROM rep_unavailability u
      WHERE u.rep_id = s.rep_id
        AND u.start_time = s.first_day::timestamp AT TIME ZONE b.timezone
  );

INSERT INTO statutory_holidays (holiday_date, name)
VALUES ('2026-11-11', 'Remembrance Day')
ON CONFLICT (holiday_date) DO NOTHING;

-- B737 bars on the Nov sheet. Tail numbers are not shown, and both run past Nov 30.
INSERT INTO maintenance_events (aircraft_type_id, mro_id, tail_number, event_type,
                                induction_date, rts_date, notes)
SELECT a.id, m.id, 'TBD', v.event_type, v.induction_date, v.rts_date,
       'From roster sheet; tail and RTS date not shown'
FROM (VALUES
    ('AAR', 'heavy_check', DATE '2026-11-01', DATE '2026-11-30'),
    ('KFL', 'heavy_check', DATE '2026-11-23', DATE '2026-11-30')
) AS v(code, event_type, induction_date, rts_date)
JOIN mro_locations m ON m.facility_name = v.code
JOIN aircraft_types a ON a.model_name = '737-800 NG'
WHERE NOT EXISTS (
    SELECT 1 FROM maintenance_events e
    WHERE e.mro_id = m.id AND e.induction_date = v.induction_date
);

-- One 07:00 local, 10 h demand per support day, as the API creates for new events.
INSERT INTO mro_demands (mro_id, aircraft_type_id, demand_type, start_time, end_time,
                         reps_needed, priority, notes, maintenance_event_id)
SELECT e.mro_id, e.aircraft_type_id, e.event_type,
       (d::date + TIME '07:00') AT TIME ZONE m.timezone,
       (d::date + TIME '17:00') AT TIME ZONE m.timezone,
       e.reps_required, 3, e.tail_number || ' ' || e.event_type, e.id
FROM maintenance_events e
JOIN mro_locations m ON m.id = e.mro_id
CROSS JOIN LATERAL generate_series(e.induction_date, e.rts_date, INTERVAL '1 day') AS d
WHERE e.event_type = 'heavy_check'
  AND e.status IN ('planned', 'in_progress')
  AND NOT EXISTS (SELECT 1 FROM mro_demands x WHERE x.maintenance_event_id = e.id);

COMMIT;

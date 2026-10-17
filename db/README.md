# Database

PostgreSQL schema for the Tech Rep Scheduler. [init.sql](init.sql) creates these tables:

| Table | Purpose |
| --- | --- |
| `tech_reps` | Technical representatives and their home base |
| `aircraft_types` | Aircraft models (for example, 737 MAX 8 or 787-9) |
| `tech_rep_certifications` | Many-to-many link between reps and the aircraft types they are certified on |
| `mro_locations` | MRO facilities where reps are sent |
| `assignments` | Scheduled rep visits to an MRO, with a time window, status, linked demand, and overtime type. A rep cannot hold two overlapping non-cancelled assignments |
| `mro_demands` | Work an MRO needs covered: aircraft type, time window, reps needed, priority, and type (`base_coverage` or `aog`) |
| `rep_unavailability` | Periods a rep cannot be scheduled: vacation, sick, training, and other leave |
| `shift_patterns` | CBA shift patterns (5-5-4, 5-2, 7-7, 4-3) with a day-by-day work/off cycle and shift length |
| `shift_start_windows` | Allowed local start times per pattern and shift (CBA 19-5) |
| `cba_rules` | Numeric CBA limits: rest, consecutive days, field service duty, overtime rates, and banked overtime cap. Date ranges cannot overlap |
| `statutory_holidays` | Holiday dates used for premium pay. Load the 11 dates yourself; the CBA does not list them |
| `pay_periods` | Pay period dates for the 8 h overtime tier. Optional: without rows, the solver uses the 1st to 15th and 16th to month end (24 a year) |
| `travel_times` | One-way travel hours from a home base to an MRO. Counts toward the duty day and is paid at the field service rate |
| `demand_responses` | Reps who accepted or declined a solicited demand. Reps who did not accept can only be assigned mandatorily |

`tech_reps` also stores classification, CBA group (1 to 5, which picks the 26- or 52-week averaging period), union seniority date, shift pattern, shift cycle start date (day 1 of the pattern, used to tell work days from days off), and banked overtime hours (0 to 80). `assignments` also stores overtime hours and one-way travel hours.

The script needs the `btree_gist` extension for its exclusion constraints and creates it if missing.

The script is idempotent, so you can run it more than once.

## Option 1: Local Postgres in Docker

Postgres runs every `.sql` file in `/docker-entrypoint-initdb.d` the first time the container starts with an empty data volume.

```sh
docker run -d --name techrep-db \
  -e POSTGRES_USER=techrep \
  -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=techrep \
  -p 5432:5432 \
  -v "$PWD/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
  postgres:16
```

Run this from the repository root. To rebuild the schema from scratch, remove the container with `docker rm -f techrep-db` and run the command again.

## Option 2: An existing Postgres server

```sh
psql "postgresql://<user>:<password>@<host>:5432/<db>" -f db/init.sql
```

## Verify

```sh
docker exec -it techrep-db psql -U techrep -d techrep -c '\dt'
```

## Backend connection settings

The backend reads its connection settings (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) from `backend/.env`. Copy [backend/.env.example](../backend/.env.example) to `backend/.env`. Its values match the Docker command above. The root `.gitignore` already excludes `.env`.

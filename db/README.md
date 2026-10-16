# Database

PostgreSQL schema for the Tech Rep Scheduler. [init.sql](init.sql) creates these tables:

| Table | Purpose |
| --- | --- |
| `tech_reps` | Technical representatives and their home base |
| `aircraft_types` | Aircraft models (for example, 737 MAX 8 or 787-9) |
| `tech_rep_certifications` | Many-to-many link between reps and the aircraft types they are certified on |
| `mro_locations` | MRO facilities where reps are sent |
| `assignments` | Scheduled rep visits to an MRO, with a time window and status |

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

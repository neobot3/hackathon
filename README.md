# Tech Rep Scheduler

Full-stack application that schedules airline Tech Reps to MRO facilities. It uses a FastAPI backend, a PostgreSQL database, and the Google OR-Tools CP-SAT solver. See [docs/problem_statement.md](docs/problem_statement.md) for the problem and [docs/architecture.md](docs/architecture.md) for the design.

## Repository layout

| Folder | Contents |
| --- | --- |
| [frontend/](frontend/) | npm project. The UI has not been added yet. |
| [backend/](backend/) | FastAPI app. See [Backend layout](#backend-layout). |
| [db/](db/) | Schema script ([init.sql](db/init.sql)) and [database instructions](db/README.md) |
| [docs/](docs/) | Architecture and problem statement |

### Backend layout

```text
backend/
├── main.py             App entry point: creates the FastAPI app and includes routers
├── config.py           Settings loaded from .env and environment variables
├── .env.example        Template for .env (copy it to .env)
├── database.py         SQLAlchemy engine, session, and get_db dependency
├── models.py           SQLAlchemy models that mirror db/init.sql
├── schemas.py          Pydantic request and response models
├── routers/
│   ├── reps.py         /reps endpoints for managing Tech Reps
│   └── schedules.py    /schedule endpoints for scheduling requests
├── services/
│   └── solver.py       Google OR-Tools CP-SAT optimization logic
├── requirements.txt
└── Dockerfile
```

### Configuration

The backend reads its settings from `backend/.env`. Environment variables with the same name take precedence over the file. To create the file:

```sh
cp backend/.env.example backend/.env
```

| Variable | Default | Description |
| --- | --- | --- |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `techrep` | Database name |
| `DB_USER` | `techrep` | Database user |
| `DB_PASSWORD` | none, required | Database password |
| `DB_DRIVER` | `postgresql+psycopg2` | SQLAlchemy driver |
| `DATABASE_URL` | not set | Full connection URL. If set, it replaces all `DB_*` values. |
| `DB_ECHO` | `false` | Log every SQL statement |
| `SOLVER_MAX_SECONDS` | `10` | Time limit for each solver run |

`.env` is excluded by `.gitignore`. Commit changes to `.env.example` only, and never put real passwords in it.

## Prerequisites

- Python 3.12 or later
- Docker Desktop, running
- Node.js and npm, for the frontend

## 1. Start the database

From the repository root:

```sh
docker run -d --name techrep-db \
  -e POSTGRES_USER=techrep \
  -e POSTGRES_PASSWORD=change-me \
  -e POSTGRES_DB=techrep \
  -p 5432:5432 \
  -v "$PWD/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
  postgres:16
```

Postgres runs `init.sql` on first start and creates the tables. To check that the tables exist:

```sh
docker exec -it techrep-db psql -U techrep -d techrep -c '\dt'
```

On later runs, start the existing container with `docker start techrep-db`. For other options, such as an existing Postgres server, see [db/README.md](db/README.md).

## 2. Start the backend

You can run the backend locally or in Docker.

### Option A: Run locally (recommended for development)

```sh
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

You only need to create the virtual environment and install packages once. On later runs:

```sh
cd backend
source .venv/bin/activate
uvicorn main:app --reload
```

### Option B: Run in Docker

```sh
docker build -t techrep-backend backend
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -e DB_HOST=host.docker.internal \
  techrep-backend
```

The image does not include `.env`, so `--env-file` passes the settings in at run time. Inside a container, `localhost` refers to the container itself, so `DB_HOST=host.docker.internal` is used to reach the database on your machine.

## 3. Check that it works

- Health check: <http://localhost:8000/health> returns `{"status": "ok"}`.
- Interactive API docs: <http://localhost:8000/docs>
- Tech Reps (needs the database): <http://localhost:8000/reps>

To call the solver endpoint:

```sh
curl -X POST http://localhost:8000/schedule/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "reps": [
      {"id": 1, "certified_aircraft_type_ids": [10]},
      {"id": 2, "certified_aircraft_type_ids": [10, 20]}
    ],
    "requests": [
      {"id": 100, "aircraft_type_id": 20},
      {"id": 101, "aircraft_type_id": 10}
    ]
  }'
```

## 4. Frontend

The frontend is an empty npm project with no framework or start script yet. Once a framework is added, install dependencies and start it:

```sh
cd frontend
npm install
npm run dev
```

## Stop everything

```sh
# Stop the backend: press Ctrl+C in its terminal
docker stop techrep-db
```

To delete the database and its data so `init.sql` runs again on the next start:

```sh
docker rm -f -v techrep-db
```

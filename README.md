# Task Manager API

A small REST API for managing tasks, built with FastAPI, SQLAlchemy 2.x and PostgreSQL.

## Status

Current stage: project skeleton — application startup, database connection, `Task`
model and Alembic migrations are in place. CRUD endpoints and tests are not
implemented yet.

## Requirements

- Python 3.12+
- PostgreSQL 14+ (local, or a hosted provider such as Neon / RDS / Supabase)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit the values
```

If you do not have a PostgreSQL instance handy, one can be started with Docker:

```bash
docker run -d --name taskmanager-db \
  -e POSTGRES_USER=taskmanager \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=taskmanager \
  -p 5432:5432 postgres:16-alpine
```

## Configuration

All configuration comes from environment variables (or a local `.env` file) and is
validated by `pydantic-settings` in `app/core/config.py`. No credentials are
committed to the repository.

| Variable       | Description                  | Default            |
| -------------- | ---------------------------- | ------------------ |
| `APP_NAME`     | Application title            | `Task Manager API` |
| `APP_VERSION`  | Application version          | `0.1.0`            |
| `DEBUG`        | Echo SQL statements          | `false`            |
| `DATABASE_URL` | PostgreSQL connection string | _required_         |

`DATABASE_URL` accepts a standard connection string and is rewritten internally to
use the psycopg 3 driver, so both of these are equivalent:

```
postgresql://user:password@host:5432/dbname
postgresql+psycopg://user:password@host:5432/dbname
```

Managed providers usually require TLS and may hand out a connection-pooler
hostname; append their parameters to the URL as-is, for example
`?sslmode=require&channel_binding=require`. Quote the value in `.env` so the `&`
is preserved.

## Database migrations

```bash
alembic upgrade head            # apply all migrations
alembic revision --autogenerate -m "description"   # create a new migration
alembic downgrade -1            # roll back the last migration
```

## Running the application

```bash
uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Interactive docs: http://127.0.0.1:8000/docs

## Project structure

```
app/
  main.py            FastAPI application entrypoint
  core/config.py     Settings loaded from environment variables
  db/database.py     Engine, session factory, declarative Base, get_db dependency
  db/models.py       SQLAlchemy models (Task, TaskStatus)
  schemas/task.py    Pydantic request/response schemas
  routes/tasks.py    Task router
alembic/             Migration environment and versions
tests/               Test suite
```

## Data model

| Field         | Type                            | Notes                        |
| ------------- | ------------------------------- | ---------------------------- |
| `id`          | integer                         | Primary key                  |
| `title`       | string(255)                     | Required                     |
| `description` | text                            | Optional                     |
| `status`      | `todo` \| `in-progress` \| `done` | Defaults to `todo`         |
| `due_date`    | date                            | Optional                     |
| `created_at`  | timestamptz                     | Set by the database          |
| `updated_at`  | timestamptz                     | Updated on write             |

## Next steps

- [ ] CRUD endpoints for tasks
- [ ] Filtering and pagination on the list endpoint
- [ ] Test suite with pytest and httpx

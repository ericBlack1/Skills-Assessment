# Task Manager API

A small REST API for managing tasks, built with FastAPI, SQLAlchemy 2.x and PostgreSQL.

## Requirements

- Python 3.12+
- PostgreSQL 14+ (local, or a hosted provider such as Neon / RDS / Supabase)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit the values
alembic upgrade head
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

| Variable       | Description                    | Default            |
| -------------- | ------------------------------ | ------------------ |
| `APP_NAME`     | Application title              | `Task Manager API` |
| `APP_VERSION`  | Application version            | `0.1.0`            |
| `DEBUG`        | Echo SQL statements            | `false`            |
| `DATABASE_URL` | PostgreSQL connection string   | _required_         |

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

## API endpoints

Base path: `/api/v1`

| Method | Path                    | Description              | Success |
| ------ | ----------------------- | ------------------------ | ------- |
| POST   | `/api/v1/tasks`         | Create a task            | 201     |
| GET    | `/api/v1/tasks`         | List tasks               | 200     |
| GET    | `/api/v1/tasks/{id}`    | Get one task             | 200     |
| PATCH  | `/api/v1/tasks/{id}`    | Partially update a task  | 200     |
| DELETE | `/api/v1/tasks/{id}`    | Delete a task            | 204     |

### Create task

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write documentation",
    "description": "Add endpoint examples to the README",
    "status": "todo",
    "due_date": "2026-10-01"
  }'
```

- `title` is required and must not be empty or only whitespace.
- `description` is optional.
- `status` is optional and defaults to `todo`.
- `due_date` is required and must be a valid date (`YYYY-MM-DD`).

Allowed status values: `todo`, `in-progress`, `done`.

### List tasks

```bash
curl http://127.0.0.1:8000/api/v1/tasks
curl "http://127.0.0.1:8000/api/v1/tasks?status=todo"
curl "http://127.0.0.1:8000/api/v1/tasks?status=in-progress"
curl "http://127.0.0.1:8000/api/v1/tasks?status=done"
```

Returns an empty JSON array when no tasks match.

### Get a task

```bash
curl http://127.0.0.1:8000/api/v1/tasks/1
```

Returns `404` with a clear message when the task does not exist.

### Update a task

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write documentation",
    "status": "in-progress"
  }'
```

Only supplied fields are updated. Returns `404` when the task does not exist.

### Delete a task

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/tasks/1
```

Returns `204 No Content` on success. Returns `404` when the task does not exist.

## Testing

```bash
pytest
```

## Project structure

```
app/
  main.py              FastAPI application entrypoint
  core/config.py       Settings loaded from environment variables
  db/database.py       Engine, session factory, declarative Base, get_db dependency
  db/models.py         SQLAlchemy models (Task, TaskStatus)
  schemas/task.py      Pydantic request/response schemas
  services/task_service.py  Database operations for tasks
  routes/tasks.py      Task HTTP routes
alembic/               Migration environment and versions
tests/                 Test suite
```

## Data model

| Field         | Type                              | Notes                |
| ------------- | --------------------------------- | -------------------- |
| `id`          | integer                           | Primary key          |
| `title`       | string(255)                       | Required             |
| `description` | text                              | Optional             |
| `status`      | `todo` \| `in-progress` \| `done` | Defaults to `todo`   |
| `due_date`    | date                              | Required on create   |
| `created_at`  | timestamptz                       | Set by the database  |
| `updated_at`  | timestamptz                       | Updated on write     |

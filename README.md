# Task Manager API

![CI](https://github.com/ericBlack1/Skills-Assessment/actions/workflows/ci.yml/badge.svg)

A REST API for managing tasks. Create, list, filter, update, and delete tasks
with validated input, persistent PostgreSQL storage, and an automated test suite.

## Features

- Full CRUD for tasks (create, list, get, update, delete)
- Filter tasks by status (`todo`, `in-progress`, `done`)
- Paginated list responses with metadata (`page`, `limit`, `total`, etc.)
- Sorting by whitelisted fields (`created_at`, `updated_at`, `due_date`, `title`, `status`)
- Input validation with clear error messages
- PostgreSQL persistence via SQLAlchemy 2.x
- Database migrations with Alembic
- 28 automated API tests with isolated test database setup
- Docker and Docker Compose for local containerized runs
- GitHub Actions CI pipeline

## Tech stack

| Layer        | Technology                          |
| ------------ | ----------------------------------- |
| Language     | Python 3.12+                        |
| Web framework| FastAPI                             |
| ORM          | SQLAlchemy 2.x                      |
| Migrations   | Alembic                             |
| Validation   | Pydantic v2, pydantic-settings      |
| Database     | PostgreSQL 14+                      |
| Testing      | Pytest, FastAPI TestClient, httpx   |
| Containers   | Docker, Docker Compose              |
| CI           | GitHub Actions                      |

## Prerequisites

- Python 3.12 or newer
- PostgreSQL 14+ (local install or hosted provider such as Neon, RDS, Supabase)
- Git

Optional (for the default test setup only):

- Docker — used by pytest to start a temporary PostgreSQL instance when
  `TEST_DATABASE_URL` is not configured

## Installation

Clone the repository and set up a virtual environment:

```bash
git clone <repository-url>
cd task-manager-api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database setup

1. Create a PostgreSQL database for the application (for example `taskmanager`).
2. Copy the environment template and set your connection string:

```bash
cp .env.example .env
```

3. Edit `.env` and set `DATABASE_URL` to point at your database. Example for a
   local PostgreSQL instance:

```env
DATABASE_URL="postgresql://taskmanager:your-password@localhost:5432/taskmanager"
```

For hosted providers, use the connection string they provide. If the URL
contains query parameters (for example `?sslmode=require`), wrap the value in
quotes in `.env`.

The application rewrites `postgresql://` URLs to use the psycopg 3 driver
automatically. No credentials are hardcoded in the source code.

## Environment variables

| Variable            | Required | Default              | Description                          |
| ------------------- | -------- | -------------------- | ------------------------------------ |
| `DATABASE_URL`      | Yes      | —                    | PostgreSQL connection string         |
| `APP_NAME`          | No       | `Task Manager API`   | API title shown in OpenAPI docs      |
| `APP_VERSION`       | No       | `0.1.0`              | API version                          |
| `DEBUG`             | No       | `false`              | When `true`, log SQL statements      |
| `TEST_DATABASE_URL` | No       | —                    | Dedicated database for pytest only   |

Settings are loaded from environment variables and an optional `.env` file in
the project root (`app/core/config.py`).

## Running migrations

Apply the database schema before starting the API:

```bash
source .venv/bin/activate
alembic upgrade head
```

Other useful commands:

```bash
alembic current                              # show current revision
alembic check                                # detect model/schema drift
alembic revision --autogenerate -m "message" # create a new migration
alembic downgrade -1                         # roll back one migration
```

## Starting the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

If port 8000 is already in use, choose another port:

```bash
uvicorn app.main:app --reload --port 8001
```

Useful URLs (default port 8000):

| URL                              | Purpose              |
| -------------------------------- | -------------------- |
| http://127.0.0.1:8000/health     | Health check         |
| http://127.0.0.1:8000/docs       | Swagger UI           |
| http://127.0.0.1:8000/redoc      | ReDoc documentation  |

## Running with Docker

Docker Compose runs the API and a PostgreSQL database together. The API waits for
PostgreSQL to become healthy before starting — no arbitrary sleep commands.

### Build and start

```bash
docker compose build
docker compose up -d
```

Optional: copy `.env.example` to `.env` and adjust `POSTGRES_USER`,
`POSTGRES_PASSWORD`, or `POSTGRES_DB`. Example defaults are built into
`docker-compose.yml` for local development only — change them before any shared
deployment.

### Run migrations

Migrations are run explicitly; the application does not auto-migrate on startup.

```bash
docker compose exec api alembic upgrade head
```

### Access the API

| URL | Purpose |
| --- | ------- |
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

### View logs

```bash
docker compose logs -f
docker compose logs -f api
docker compose logs -f db
```

### Stop services

```bash
docker compose down
```

PostgreSQL data is stored in the named Docker volume `postgres_data` and survives
`docker compose down`. Remove the volume as well with:

```bash
docker compose down -v
```

## Running tests

Tests use an isolated database and never touch your application `DATABASE_URL`
unless you explicitly set `TEST_DATABASE_URL` to the same value (which is
blocked).

**Default:** pytest starts a temporary PostgreSQL container, runs the suite, and
cleans up automatically. Docker must be installed and running.

```bash
source .venv/bin/activate
pytest
```

Verbose output:

```bash
pytest -v
```

**Alternative:** provide a dedicated test database:

```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/taskmanager_test"
pytest
```

Each test runs inside a rolled-back transaction, so tests are deterministic and
leave no data behind.

### Continuous integration

GitHub Actions runs the full test suite automatically on every push and pull
request (`.github/workflows/ci.yml`). The workflow:

1. Checks out the code
2. Sets up Python 3.12 with pip caching
3. Starts a PostgreSQL 16 service container with a health check
4. Runs `alembic upgrade head`
5. Runs `pytest -v`

The pipeline uses ephemeral test credentials and does not require a local `.env`
file, developer PostgreSQL installation, or external services. The workflow
fails if any test fails.

## API endpoints

Base path: `/api/v1`

| Method | Path                   | Description             | Success code |
| ------ | ---------------------- | ----------------------- | ------------ |
| POST   | `/api/v1/tasks`        | Create a task           | 201          |
| GET    | `/api/v1/tasks`        | List tasks (paginated)  | 200          |
| GET    | `/api/v1/tasks/{id}`   | Get one task            | 200          |
| PATCH  | `/api/v1/tasks/{id}`   | Partially update a task | 200          |
| DELETE | `/api/v1/tasks/{id}`   | Delete a task           | 204          |

### Task fields

| Field         | Type                              | Create | Update | Notes                    |
| ------------- | --------------------------------- | ------ | ------ | ------------------------ |
| `title`       | string (max 255)                  | Required | Optional | Cannot be empty/whitespace |
| `description` | string                            | Optional | Optional |                          |
| `status`      | `todo` \| `in-progress` \| `done` | Optional | Optional | Defaults to `todo` on create |
| `due_date`    | date (`YYYY-MM-DD`)               | Required | Optional |                          |
| `id`          | integer                           | —      | —      | Assigned by the database |
| `created_at`  | datetime (UTC)                    | —      | —      | Set by the database      |
| `updated_at`  | datetime (UTC)                    | —      | —      | Updated on write         |

## Example requests and responses

### Create a task

**Request**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write documentation",
    "description": "Add README examples",
    "status": "todo",
    "due_date": "2026-10-01"
  }'
```

**Response — 201 Created**

```json
{
  "id": 1,
  "title": "Write documentation",
  "description": "Add README examples",
  "status": "todo",
  "due_date": "2026-10-01",
  "created_at": "2026-09-24T00:00:00.000000Z",
  "updated_at": "2026-09-24T00:00:00.000000Z"
}
```

### List tasks (filter, pagination, sorting)

```bash
curl http://127.0.0.1:8000/api/v1/tasks
curl "http://127.0.0.1:8000/api/v1/tasks?status=in-progress&page=2&limit=20"
curl "http://127.0.0.1:8000/api/v1/tasks?sort_by=due_date&sort_order=asc"
curl "http://127.0.0.1:8000/api/v1/tasks?status=todo&page=1&limit=20&sort_by=due_date&sort_order=asc"
```

Query parameters:

| Parameter    | Default      | Constraints   | Description                          |
| ------------ | ------------ | ------------- | ------------------------------------ |
| `status`     | —            | enum          | Filter by task status                |
| `page`       | `1`          | `>= 1`        | Page number                          |
| `limit`      | `10`         | `1`–`100`     | Tasks per page                       |
| `sort_by`    | `created_at` | whitelist     | `created_at`, `updated_at`, `due_date`, `title`, `status` |
| `sort_order` | `desc`       | `asc` / `desc`| Sort direction                       |

**Response — 200 OK**

```json
{
  "data": [
    {
      "id": 1,
      "title": "Write documentation",
      "description": "Add README examples",
      "status": "in-progress",
      "due_date": "2026-10-01",
      "created_at": "2026-09-24T00:00:00.000000Z",
      "updated_at": "2026-09-24T00:00:00.000000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 47,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

`total` reflects the number of tasks matching the filter, not the entire table.
Returns `"data": []` with accurate pagination metadata when no tasks match.

### Get a task

```bash
curl http://127.0.0.1:8000/api/v1/tasks/1
```

**Response — 200 OK** — same shape as a single task object above.

**Response — 404 Not Found**

```json
{
  "detail": "Task with id 1 not found"
}
```

### Update a task (partial)

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Response — 200 OK** — returns the updated task object.

### Delete a task

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/tasks/1
```

**Response — 204 No Content** — empty body on success.

## Validation and error behavior

| Situation                         | HTTP status | Example detail                                      |
| --------------------------------- | ----------- | --------------------------------------------------- |
| Missing required field            | 422         | Pydantic validation error listing the field         |
| Empty or whitespace-only title    | 422         | `title must not be empty or only whitespace`        |
| Invalid status value              | 422         | Enum validation error for `status`                  |
| Invalid date format               | 422         | Date parsing error for `due_date`                   |
| Invalid `page` or `limit`         | 422         | Out-of-range pagination query parameter             |
| Invalid `sort_by` or `sort_order` | 422         | Enum validation error                               |
| Task not found                    | 404         | `Task with id {id} not found`                       |
| Database error                    | 500         | `A database error occurred. Please try again later.`|

Validation errors (422) return a JSON body with a `detail` array describing
each failing field. Database errors are never exposed with raw SQL or stack
traces.

## Project structure

```
app/
  main.py                   Application entrypoint and error handlers
  core/config.py            Environment-based settings
  db/database.py            Engine, session factory, get_db dependency
  db/models.py              SQLAlchemy Task model and TaskStatus enum
  schemas/task.py           Pydantic request/response schemas
  services/task_service.py  Database operations
  routes/tasks.py             HTTP route handlers
alembic/                    Migration environment and versions
tests/
  conftest.py               Test database fixtures
  test_tasks.py             CRUD and validation tests
  test_list_pagination.py   Pagination and sorting tests
```

## Scaling to 1 Million Users

This project is a focused assignment implementation: a single FastAPI service talking
directly to PostgreSQL. It is **not** production-ready for one million users today.
The current design is intentionally simple, but the architecture can evolve in
clear stages as traffic and data grow.

**Application layer.** The API is stateless meaning no session data is stored in memory between requests, so you can run multiple Uvicorn/Gunicorn workers behind a load balancer (AWS ALB, NGINX, etc.) and scale horizontally by adding instances when CPU or latency rises. Keep business logic in the service layer and avoid per-instance state so any worker can handle any request.

**Database.** Move to a managed PostgreSQL service with automated backups, failover,
and connection pooling (PgBouncer or the provider's pooler). The indexes on
`status`, `due_date`, and `created_at` support common filter/sort patterns, but
you would still monitor slow queries and adjust indexes based on real traffic. When
read volume dominates, add read replicas for list endpoints while keeping writes on
the primary. Table partitioning is a later step only worth it when row counts and
query patterns make maintenance or scan cost a measured problem, not upfront.

**Caching.** Introduce Redis for data that is read often and changes infrequently
(for example a cached task count or popular filtered views). Cache keys must include
filter/sort parameters, and every create/update/delete must invalidate or update the
relevant entries. Blind caching creates stale reads; explicit invalidation rules are
part of the design.

**Background processing.** Email reminders, exports, analytics, and other slow work
should move to background workers (Celery/RQ or a managed queue) so API responses
stay fast. The HTTP layer validates input, writes to PostgreSQL, enqueues work, and
returns, it does not perform heavy computation inline.

**Infrastructure sketch.** A realistic growth path looks like:

```
Client → Load Balancer → Multiple FastAPI instances → PostgreSQL (+ pooler)
                                                     → Redis (cache)
                                                     → Background workers (queue)
```

**Observability and security.** Production would add centralized logging, metrics
(request latency, error rate, pool usage), health checks on each instance, and error
tracking (Sentry, etc.) with alerting. Security layers include HTTPS termination,
authentication/authorization, rate limiting at the gateway, and secrets stored in a
manager rather than plain `.env` files on servers.

The point is separation of concerns: the code you have now proves the domain logic
works; reaching large scale means adding infrastructure around it, not rewriting
the core API from scratch.

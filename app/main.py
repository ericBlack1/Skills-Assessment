from fastapi import FastAPI

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.routes import tasks

app = FastAPI(title=settings.app_name, version=settings.app_version)

register_exception_handlers(app)

app.include_router(tasks.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

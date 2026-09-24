from fastapi import FastAPI

from app.core.config import settings
from app.routes import tasks

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(tasks.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

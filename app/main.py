from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db.database import get_db
from app.routes import auth, tasks

app = FastAPI(title=settings.app_name, version=settings.app_version)

register_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/health", tags=["health"])
def health_check(db: DbSession) -> dict[str, str]:
    """Liveness check including database connectivity."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

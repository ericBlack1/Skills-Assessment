import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.routes import tasks

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(tasks.router, prefix="/api/v1")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    _request: Request, _exc: SQLAlchemyError
) -> JSONResponse:
    logger.exception("Database error")
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

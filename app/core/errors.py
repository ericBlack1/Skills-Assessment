from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class APIError(Exception):
    """Application error with a safe, client-facing representation."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.code = code
        self.details = details


def build_error_response(
    status_code: int,
    message: str,
    code: str,
    details: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "statusCode": status_code,
            "message": message,
            "data": None,
            "error": {
                "code": code,
                "details": details,
            },
        },
    )


def task_not_found() -> APIError:
    return APIError(
        status_code=404,
        message="Task not found",
        code="TASK_NOT_FOUND",
        details=None,
    )


def email_already_registered() -> APIError:
    return APIError(
        status_code=409,
        message="Email already registered",
        code="EMAIL_ALREADY_REGISTERED",
        details=None,
    )


def invalid_credentials() -> APIError:
    return APIError(
        status_code=401,
        message="Invalid email or password",
        code="INVALID_CREDENTIALS",
        details=None,
    )


def unauthorized() -> APIError:
    return APIError(
        status_code=401,
        message="Authentication required",
        code="UNAUTHORIZED",
        details=None,
    )


def invalid_token() -> APIError:
    return APIError(
        status_code=401,
        message="Invalid or expired token",
        code="INVALID_TOKEN",
        details=None,
    )


def _format_validation_details(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for error in errors:
        location = [
            str(part)
            for part in error.get("loc", ())
            if part not in {"body", "query", "path"}
        ]
        field = ".".join(location) if location else str(error.get("loc", ["request"])[-1])
        formatted.append(
            {
                "field": field,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
        )
    return formatted


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return build_error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        details=exc.details,
    )


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return build_error_response(
        status_code=422,
        message="Validation failed",
        code="VALIDATION_ERROR",
        details=_format_validation_details(exc.errors()),
    )


async def database_error_handler(
    _request: Request, _exc: SQLAlchemyError
) -> JSONResponse:
    return build_error_response(
        status_code=500,
        message="A database error occurred",
        code="DATABASE_ERROR",
        details=None,
    )


async def unexpected_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return build_error_response(
        status_code=500,
        message="An unexpected error occurred",
        code="INTERNAL_SERVER_ERROR",
        details=None,
    )


def register_exception_handlers(app: Any) -> None:
    import logging

    logger = logging.getLogger(__name__)

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return await api_error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return await validation_error_handler(request, exc)

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("Database error")
        return await database_error_handler(request, exc)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error")
        return await unexpected_error_handler(request, exc)

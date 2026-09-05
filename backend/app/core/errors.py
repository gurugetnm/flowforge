"""Application error types and their HTTP representation.

Every failure the API raises deliberately carries a stable machine readable
``code`` alongside a human readable message, so the client can branch on the
code and still show something useful without translating status numbers.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for expected, client visible failures."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class WorkflowInvalidError(AppError):
    """Raised when a workflow cannot be executed as configured."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "workflow_invalid"


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that render errors in a single consistent shape."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_payload()})

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> Any:
        if isinstance(exc.detail, str):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": {"code": "http_error", "message": exc.detail}},
                headers=exc.headers,
            )
        return await http_exception_handler(request, exc)

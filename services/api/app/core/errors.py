from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_INTERNAL = "internal_error"
ERROR_NOT_FOUND = "not_found"
ERROR_UNAUTHENTICATED = "unauthenticated"
ERROR_FORBIDDEN = "forbidden"
ERROR_VALIDATION = "validation_error"
ERROR_HTTP = "http_error"

_STATUS_CODES = {
    401: ERROR_UNAUTHENTICATED,
    403: ERROR_FORBIDDEN,
    404: ERROR_NOT_FOUND,
}


def error_code_for_status(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, ERROR_HTTP)


def error_body(code: str, message: str, request_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body(ERROR_INTERNAL, "An unexpected error occurred.", _request_id(request)),
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body(ERROR_NOT_FOUND, "Resource not found.", _request_id(request)),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(error_code_for_status(exc.status_code), detail, _request_id(request)),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(ERROR_VALIDATION, "Request validation failed.", _request_id(request)),
    )

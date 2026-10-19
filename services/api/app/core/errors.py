from fastapi import Request
from fastapi.responses import JSONResponse

ERROR_INTERNAL = "internal_error"
ERROR_NOT_FOUND = "not_found"


def error_body(code: str, message: str, request_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content=error_body(ERROR_INTERNAL, "An unexpected error occurred.", request_id),
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=404,
        content=error_body(ERROR_NOT_FOUND, "Resource not found.", request_id),
    )

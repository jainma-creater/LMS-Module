"""Authentication and authorization error types and their HTTP handlers.

These are deliberately distinct so authentication failures (who are you?) and
authorization failures (are you allowed?) return different status codes with a
consistent error envelope and, for 401, a ``WWW-Authenticate`` challenge.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import error_body


class AuthenticationError(Exception):
    """Raised when a request has no valid, verifiable identity."""

    error_code = "unauthenticated"
    message = "Authentication required."


class AuthorizationError(Exception):
    """Raised when an authenticated principal lacks the required permission."""

    error_code = "forbidden"
    message = "You do not have permission to perform this action."


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def authentication_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body(
            AuthenticationError.error_code, AuthenticationError.message, _request_id(request)
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authorization_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=error_body(
            AuthorizationError.error_code, AuthorizationError.message, _request_id(request)
        ),
    )

"""Request-scoped context shared across middleware, dependencies, and logging.

Context variables are set per request so log records and audit events can be
correlated without threading parameters through every function.
"""

import contextvars

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
actor_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("actor_id", default=None)

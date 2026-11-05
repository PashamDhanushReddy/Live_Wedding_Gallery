"""
Context variable management for request and background task correlation.
Thread-safe and async-safe across ASGI, WSGI, Daphne, and Celery.
"""

import contextvars
from typing import Optional

_correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)
_upload_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'upload_id', default=None
)
_wedding_slug_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'wedding_slug', default=None
)


def get_correlation_id() -> Optional[str]:
    """Returns the current request or task correlation ID."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Sets the correlation ID for the current context."""
    _correlation_id_ctx.set(correlation_id)


def get_upload_id() -> Optional[str]:
    """Returns the current photo upload ID if set."""
    return _upload_id_ctx.get()


def set_upload_id(upload_id: str) -> None:
    """Sets the photo upload ID for the current context."""
    _upload_id_ctx.set(upload_id)


def get_wedding_slug() -> Optional[str]:
    """Returns the current wedding slug if set."""
    return _wedding_slug_ctx.get()


def set_wedding_slug(wedding_slug: str) -> None:
    """Sets the wedding slug for the current context."""
    _wedding_slug_ctx.set(wedding_slug)


def clear_context() -> None:
    """Clears all observability context variables."""
    _correlation_id_ctx.set(None)
    _upload_id_ctx.set(None)
    _wedding_slug_ctx.set(None)


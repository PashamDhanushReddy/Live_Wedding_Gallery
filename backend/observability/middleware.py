"""
Production Observability Middleware for Live Wedding Gallery.
- Injects & propagates X-Correlation-ID across all requests.
- Measures request latencies and records status distributions.
- Detects slow database queries (>200ms).
- Emits structured access logs without leaking sensitive data.
"""

import time
import uuid
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.db import connection

from .context import set_correlation_id, set_upload_id, set_wedding_slug, clear_context
from .metrics import metrics
from .logging_formatters import sanitize_dict

logger = logging.getLogger('observability.access')


class ObservabilityMiddleware:
    """HTTP middleware capturing latencies, error distributions, and correlation IDs."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.perf_counter()

        # 1. Extract or generate Correlation ID
        correlation_id = (
            request.headers.get('X-Correlation-ID') or
            request.headers.get('X-Request-ID') or
            request.headers.get('X-Upload-ID') or
            uuid.uuid4().hex
        )
        set_correlation_id(correlation_id)

        # 2. Extract Upload ID if present
        upload_id = request.headers.get('X-Upload-ID')
        if not upload_id and request.method == 'POST':
            upload_id = request.POST.get('upload_id')
        if upload_id:
            set_upload_id(str(upload_id))

        # 3. Extract Wedding Slug if present in URL path
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 3 and path_parts[0] == 'api' and path_parts[1] == 'weddings':
            set_wedding_slug(path_parts[2])

        # Track initial DB query count for query profiling
        initial_queries = len(connection.queries) if connection.queries else 0

        try:
            response = self.get_response(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            metrics.record_request(500, duration_ms)
            logger.error(
                f"Unhandled 500 exception during request {request.method} {request.path}: {exc}",
                exc_info=True,
                extra={'event': 'HTTP_UNHANDLED_EXCEPTION', 'correlation_id': correlation_id}
            )
            clear_context()
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Record metrics
        metrics.record_request(response.status_code, duration_ms)

        # Check slow queries if debug query logging is active
        if connection.queries and len(connection.queries) > initial_queries:
            for q in connection.queries[initial_queries:]:
                q_time = float(q.get('time', 0.0)) * 1000.0
                if q_time > 200.0:  # > 200ms is slow
                    metrics.record_slow_query(q.get('sql', ''), q_time)

        # Attach Correlation ID to response headers
        response['X-Correlation-ID'] = correlation_id

        # Emit structured access log
        if not request.path.startswith('/static/') and not request.path == '/api/health/':
            log_level = logging.INFO
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING

            logger.log(
                log_level,
                f"{request.method} {request.path} {response.status_code} ({duration_ms:.1f}ms)",
                extra={
                    'event': 'API_REQUEST_COMPLETED',
                    'correlation_id': correlation_id,
                    'upload_id': upload_id,
                    'extra_data': {
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration_ms': round(duration_ms, 2),
                    }
                }
            )

        clear_context()
        return response


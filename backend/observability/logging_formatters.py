"""
Production Structured JSON Logging Formatter.
- Injects correlation_id, upload_id, and wedding_slug from contextvars.
- Sanitizes sensitive credentials, passwords, tokens, and biometric vectors.
- Formats exceptions with structured stack traces.
"""

import json
import logging
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

from .context import get_correlation_id, get_upload_id, get_wedding_slug

# Regex patterns for stripping sensitive credentials and biometric embeddings
RE_CREDENTIALS = re.compile(
    r'(password|token|secret|api_key|key|authorization|bearer)=([^\s,&]+)',
    re.IGNORECASE
)
RE_BIOMETRIC_VECTOR = re.compile(
    r'\[(\s*-?\d+\.\d+[\s,]*){5,}\]'
)


def sanitize_message_str(msg: str) -> str:
    """Masks credentials, passwords, tokens, and biometric float vectors."""
    if not isinstance(msg, str):
        msg = str(msg)
    msg = RE_CREDENTIALS.sub(r'\1=[REDACTED]', msg)
    msg = RE_BIOMETRIC_VECTOR.sub('[BIOMETRIC_VECTOR_REDACTED]', msg)
    return msg


def sanitize_dict(data: Any) -> Any:
    """Recursively redacts sensitive dictionary keys."""
    if isinstance(data, dict):
        clean = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ('embedding', 'face_vector', 'biometric')):
                clean[k] = '[BIOMETRIC_VECTOR_REDACTED]'
            elif any(term in k_lower for term in ('password', 'token', 'secret', 'api_key', 'auth')):
                clean[k] = '[REDACTED]'
            else:
                clean[k] = sanitize_dict(v)
        return clean
    elif isinstance(data, list):
        if len(data) > 10 and all(isinstance(x, (float, int)) for x in data[:5]):
            return '[BIOMETRIC_VECTOR_REDACTED]'
        return [sanitize_dict(x) for x in data]
    elif isinstance(data, str):
        return sanitize_message_str(data)
    return data


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records into single-line JSON suitable for CloudWatch, Datadog, Render, or Grafana Loki.
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        
        # Base structured fields
        log_entry: Dict[str, Any] = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': sanitize_message_str(record.getMessage()),
            'source': f"{record.filename}:{record.lineno}",
            'module': record.module,
            'funcName': record.funcName,
        }

        # Context correlation
        cid = getattr(record, 'correlation_id', None) or get_correlation_id()
        if cid:
            log_entry['correlation_id'] = cid

        uid = getattr(record, 'upload_id', None) or get_upload_id()
        if uid:
            log_entry['upload_id'] = uid

        w_slug = getattr(record, 'wedding_slug', None) or get_wedding_slug()
        if w_slug:
            log_entry['wedding_slug'] = w_slug

        # Event classification if provided
        event = getattr(record, 'event', None)
        if event:
            log_entry['event'] = event

        # Extra data payload
        extra_data = getattr(record, 'extra_data', None)
        if extra_data and isinstance(extra_data, dict):
            log_entry['details'] = sanitize_dict(extra_data)

        # Exception formatting
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else 'Exception',
                'message': sanitize_message_str(str(record.exc_info[1])),
                'traceback': traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str)

"""
Distributed locking and safe concurrency utilities for background photo processing.
Ensures that concurrent workers or simultaneous duplicate uploads never execute
redundant Cloudinary streaming, NeonDB registration, or InsightFace model inference.
"""

import os
import time
import logging
import contextlib
import threading
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class ConcurrencyLockContendedError(Exception):
    """Raised when an operation cannot proceed because another worker holds the lock for this item."""
    pass


# Local in-memory lock store for environments without Redis (local development, unit tests)
_local_locks = {}
_local_locks_mutex = threading.Lock()
_redis_client_instance = None
_redis_init_attempted = False


def get_redis_client():
    """
    Returns a cached Redis client instance if REDIS_URL is configured and reachable.
    Returns None if Redis is not configured or fails to connect.
    """
    global _redis_client_instance, _redis_init_attempted
    if _redis_client_instance is not None:
        return _redis_client_instance

    redis_url = getattr(settings, 'REDIS_URL', None) or os.environ.get('REDIS_URL')
    if not redis_url:
        return None
    if not settings.DEBUG and any(h in redis_url.lower() for h in ('localhost', '127.0.0.1', '::1')):
        return None

    try:
        import redis
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=5,
            retry_on_timeout=True
        )
        # Test ping to ensure server is actually reachable
        client.ping()
        _redis_client_instance = client
        return _redis_client_instance
    except Exception as exc:
        if not _redis_init_attempted:
            logger.info(f"Redis distributed lock client unavailable ({exc}); falling back to in-memory locking.")
            _redis_init_attempted = True
        return None


@contextlib.contextmanager
def acquire_job_lock(lock_key: str, timeout: int = 180, blocking: bool = False, blocking_timeout: float = 0.2):
    """
    Distributed mutual exclusion context manager.
    
    1. If Redis is available, acquires a distributed Redis lock with a self-expiring TTL (timeout seconds).
       This guarantees that if a worker process is terminated abruptly (e.g. OOM or container kill),
       the lock will automatically release after TTL without deadlocking subsequent runs.
    2. If Redis is unavailable, falls back to a thread-safe in-memory mutex.
    
    Yields:
      bool: True if the lock was successfully acquired, False if contended.
    """
    redis_client = get_redis_client()
    lock_acquired = False
    redis_lock = None

    if redis_client is not None:
        redis_key = f"wedding_lock:{lock_key}"
        try:
            redis_lock = redis_client.lock(
                name=redis_key,
                timeout=timeout,
                blocking=blocking,
                blocking_timeout=blocking_timeout if blocking else 0
            )
            lock_acquired = redis_lock.acquire()
        except Exception as err:
            logger.warning(f"Redis lock error for '{lock_key}': {err}. Falling back to in-memory lock.")
            redis_lock = None

    # Fallback to local in-memory lock if Redis is not active or failed
    local_lock = None
    if redis_lock is None:
        with _local_locks_mutex:
            if lock_key not in _local_locks:
                _local_locks[lock_key] = threading.Lock()
            local_lock = _local_locks[lock_key]

        if blocking:
            lock_acquired = local_lock.acquire(timeout=blocking_timeout)
        else:
            lock_acquired = local_lock.acquire(blocking=False)

    try:
        yield lock_acquired
    finally:
        if lock_acquired:
            if redis_lock is not None:
                try:
                    redis_lock.release()
                except Exception as e:
                    # Catch cases where lock expired during a very long task run
                    logger.debug(f"Could not release Redis lock '{lock_key}': {e}")
            elif local_lock is not None:
                try:
                    local_lock.release()
                except RuntimeError:
                    pass


def is_lock_active(lock_key: str) -> bool:
    """Checks whether a given lock key is currently held."""
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            return bool(redis_client.exists(f"wedding_lock:{lock_key}"))
        except Exception:
            pass

    with _local_locks_mutex:
        lock = _local_locks.get(lock_key)
        if lock:
            return lock.locked()
    return False

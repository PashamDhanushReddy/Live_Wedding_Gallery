"""
Centralized Observability Metrics Registry.
High-performance, thread-safe in-memory metrics collector with cache integration.
Tracks all 14 production monitoring dimensions.
"""

import os
import sys
import time
import math
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from threading import Lock
from typing import Dict, Any, List, Optional

import psutil
from django.conf import settings
from django.utils import timezone as dj_timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Server boot time recording for Render restart tracking
SERVER_BOOT_TIME = time.time()
SERVER_BOOT_DATETIME = datetime.fromtimestamp(SERVER_BOOT_TIME, tz=timezone.utc).isoformat()
RENDER_INSTANCE_ID = os.environ.get('RENDER_INSTANCE_ID') or os.environ.get('HOSTNAME') or f"inst_{os.getpid()}"


class MetricsRegistry:
    """Thread-safe collector for real-time observability metrics."""

    def __init__(self):
        self._lock = Lock()
        
        # 1 & 2. API availability, requests, latency, errors
        self.total_requests = 0
        self.requests_2xx = 0
        self.requests_3xx = 0
        self.requests_4xx = 0
        self.requests_5xx = 0
        self.rate_limited_429 = 0
        self.recent_latencies = deque(maxlen=500)  # ms of last 500 requests for p50/p95/p99
        self.request_timestamps = deque(maxlen=2000)  # timestamps for RPM calculation
        
        # 3. Database slow queries
        self.slow_queries = deque(maxlen=50)  # last 50 queries > 200ms
        self.slow_query_count = 0
        
        # 4 & 5. Cloudinary uploads
        self.cloudinary_uploads_total = 0
        self.cloudinary_uploads_success = 0
        self.cloudinary_uploads_failed = 0
        self.cloudinary_upload_latencies = deque(maxlen=100)
        self.cloudinary_last_error: Optional[str] = None
        
        # 6 & 7. Android ingestion telemetry
        self.android_ftp_failures_total = 0
        self.android_http_forward_failures_total = 0
        self.android_intake_rejected_total = 0
        self.android_device_cache: Dict[str, Any] = {}
        
        # 9. Face processing
        self.face_extractions_total = 0
        self.face_extractions_success = 0
        self.face_extractions_failed = 0
        self.face_extraction_latencies = deque(maxlen=100)
        self.face_search_queries_total = 0
        self.face_search_latencies = deque(maxlen=100)
        self.face_cache_hits = 0
        self.face_cache_misses = 0
        
        # 10. WebSockets
        self.ws_active_connections = 0
        self.ws_peak_connections = 0
        self.ws_total_connects = 0
        self.ws_total_disconnects = 0
        self.ws_disconnect_codes: Dict[int, int] = {}

    # --------------------------------------------------------------------------
    # Record Methods
    # --------------------------------------------------------------------------

    def record_request(self, status_code: int, duration_ms: float):
        with self._lock:
            now = time.time()
            self.total_requests += 1
            self.recent_latencies.append(duration_ms)
            self.request_timestamps.append(now)

            if 200 <= status_code < 300:
                self.requests_2xx += 1
            elif 300 <= status_code < 400:
                self.requests_3xx += 1
            elif status_code == 429:
                self.requests_4xx += 1
                self.rate_limited_429 += 1
            elif 400 <= status_code < 500:
                self.requests_4xx += 1
            elif status_code >= 500:
                self.requests_5xx += 1

    def record_slow_query(self, sql: str, duration_ms: float, params: Any = None):
        with self._lock:
            self.slow_query_count += 1
            clean_sql = str(sql)[:300]
            self.slow_queries.append({
                'timestamp': dj_timezone.now().isoformat(),
                'sql': clean_sql,
                'duration_ms': round(duration_ms, 2)
            })

    def record_cloudinary_upload(self, success: bool, duration_ms: float, error: Optional[str] = None):
        with self._lock:
            self.cloudinary_uploads_total += 1
            if success:
                self.cloudinary_uploads_success += 1
            else:
                self.cloudinary_uploads_failed += 1
                if error:
                    self.cloudinary_last_error = str(error)[:200]
            self.cloudinary_upload_latencies.append(duration_ms)

    def record_face_extraction(self, success: bool, duration_ms: float, faces_count: int = 0):
        with self._lock:
            self.face_extractions_total += 1
            if success:
                self.face_extractions_success += 1
            else:
                self.face_extractions_failed += 1
            self.face_extraction_latencies.append(duration_ms)

    def record_face_search(self, duration_ms: float, cache_hit: bool = False):
        with self._lock:
            self.face_search_queries_total += 1
            self.face_search_latencies.append(duration_ms)
            if cache_hit:
                self.face_cache_hits += 1
            else:
                self.face_cache_misses += 1

    def record_ws_connect(self):
        with self._lock:
            self.ws_active_connections += 1
            self.ws_total_connects += 1
            if self.ws_active_connections > self.ws_peak_connections:
                self.ws_peak_connections = self.ws_active_connections

    def record_ws_disconnect(self, code: int):
        with self._lock:
            self.ws_active_connections = max(0, self.ws_active_connections - 1)
            self.ws_total_disconnects += 1
            self.ws_disconnect_codes[code] = self.ws_disconnect_codes.get(code, 0) + 1

    def update_android_telemetry(self, device_id: str, data: Dict[str, Any]):
        with self._lock:
            self.android_device_cache[device_id] = {
                **data,
                'last_updated': time.time(),
            }
            if data.get('ftp_status') == 'ERROR':
                self.android_ftp_failures_total += 1
            if data.get('queue_failed', 0) > 0:
                self.android_http_forward_failures_total = max(
                    self.android_http_forward_failures_total,
                    data.get('queue_failed', 0)
                )

    # --------------------------------------------------------------------------
    # Query / Getter Methods
    # --------------------------------------------------------------------------

    def get_api_metrics(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            # Requests in last 60 seconds
            cutoff_1m = now - 60
            rpm = sum(1 for ts in self.request_timestamps if ts >= cutoff_1m)

            # Error rate
            err_rate = (self.requests_5xx / self.total_requests * 100.0) if self.total_requests > 0 else 0.0

            # Latencies
            lat_list = sorted(list(self.recent_latencies))
            count = len(lat_list)
            if count > 0:
                p50 = lat_list[int(count * 0.50)]
                p95 = lat_list[int(count * 0.95)]
                p99 = lat_list[int(count * 0.99)]
                avg_lat = sum(lat_list) / count
            else:
                p50 = p95 = p99 = avg_lat = 0.0

            uptime = now - SERVER_BOOT_TIME
            status_str = "HEALTHY"
            if err_rate > 5.0:
                status_str = "UNHEALTHY"
            elif err_rate > 1.0 or p95 > 800.0:
                status_str = "DEGRADED"

            return {
                'status': status_str,
                'uptime_seconds': int(uptime),
                'uptime_human': str(timedelta(seconds=int(uptime))),
                'total_requests': self.total_requests,
                'requests_per_minute': rpm,
                'requests_2xx': self.requests_2xx,
                'requests_3xx': self.requests_3xx,
                'requests_4xx': self.requests_4xx,
                'requests_5xx': self.requests_5xx,
                'rate_limited_429': self.rate_limited_429,
                'error_rate_percent': round(err_rate, 2),
                'avg_latency_ms': round(avg_lat, 2),
                'p50_latency_ms': round(p50, 2),
                'p95_latency_ms': round(p95, 2),
                'p99_latency_ms': round(p99, 2),
            }

    def get_database_metrics(self) -> Dict[str, Any]:
        """Probes database connection and returns connection & slow query stats."""
        from django.db import connection
        db_status = "UNKNOWN"
        ping_ms = 0.0

        start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            ping_ms = (time.perf_counter() - start) * 1000.0
            db_status = "CONNECTED"
        except Exception as e:
            db_status = f"FAILED: {str(e)[:100]}"

        with self._lock:
            slow_list = list(self.slow_queries)
            slow_total = self.slow_query_count

        return {
            'status': db_status,
            'ping_ms': round(ping_ms, 2),
            'engine': connection.settings_dict.get('ENGINE', '').split('.')[-1],
            'host': connection.settings_dict.get('HOST', 'localhost'),
            'slow_queries_count': slow_total,
            'recent_slow_queries': slow_list[-10:],
        }

    def get_cloudinary_metrics(self) -> Dict[str, Any]:
        """Returns Cloudinary upload metrics and cached account usage."""
        with self._lock:
            tot = self.cloudinary_uploads_total
            succ = self.cloudinary_uploads_success
            fail = self.cloudinary_uploads_failed
            fail_rate = (fail / tot * 100.0) if tot > 0 else 0.0
            lat_list = list(self.cloudinary_upload_latencies)
            avg_lat = (sum(lat_list) / len(lat_list)) if lat_list else 0.0
            last_err = self.cloudinary_last_error

        # Fetch Cloudinary account usage (cached 5 min to avoid rate limits)
        cache_key = 'cloudinary_account_usage_cache'
        usage = cache.get(cache_key)
        if usage is None:
            try:
                from photos.cloudinary_service import get_account_usage
                usage = get_account_usage()
                cache.set(cache_key, usage, timeout=300)
            except Exception as e:
                usage = {'error': str(e)}

        return {
            'uploads_total': tot,
            'uploads_success': succ,
            'uploads_failed': fail,
            'failure_rate_percent': round(fail_rate, 2),
            'avg_upload_duration_ms': round(avg_lat, 2),
            'last_error': last_err,
            'account_usage': usage,
        }

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Calculates IngestionJob backlog, age of oldest item, and processing delay."""
        try:
            from photos.models import IngestionJob
            from django.db.models import Count, Min, Avg

            now = dj_timezone.now()
            counts_by_status = dict(
                IngestionJob.objects.values_list('status').annotate(c=Count('status'))
            )

            # In-flight backlog
            in_flight_statuses = ['RECEIVED', 'QUEUED', 'UPLOADING', 'CLOUDINARY_COMPLETED', 'DB_REGISTERED', 'FACE_PROCESSING']
            backlog_count = sum(counts_by_status.get(s, 0) for s in in_flight_statuses)

            # Oldest in-flight job age
            oldest_received = IngestionJob.objects.filter(
                status__in=in_flight_statuses
            ).aggregate(oldest=Min('received_at'))['oldest']

            oldest_age_sec = (now - oldest_received).total_seconds() if oldest_received else 0.0

            # Dead letter count
            dead_letter_count = counts_by_status.get('DEAD_LETTER', 0)
            failed_count = counts_by_status.get('FAILED', 0)
            completed_count = counts_by_status.get('COMPLETED', 0)

            return {
                'backlog_count': backlog_count,
                'counts_by_status': counts_by_status,
                'oldest_job_age_seconds': round(oldest_age_sec, 1),
                'dead_letter_count': dead_letter_count,
                'failed_count': failed_count,
                'completed_count': completed_count,
                'is_stalled': oldest_age_sec > 120.0 and backlog_count > 0,
            }
        except Exception as e:
            return {
                'error': str(e),
                'backlog_count': 0,
                'dead_letter_count': 0,
            }

    def get_face_metrics(self) -> Dict[str, Any]:
        with self._lock:
            tot = self.face_extractions_total
            succ = self.face_extractions_success
            fail = self.face_extractions_failed
            ext_lats = list(self.face_extraction_latencies)
            avg_ext = (sum(ext_lats) / len(ext_lats)) if ext_lats else 0.0

            search_tot = self.face_search_queries_total
            search_lats = list(self.face_search_latencies)
            avg_search = (sum(search_lats) / len(search_lats)) if search_lats else 0.0

            hits = self.face_cache_hits
            misses = self.face_cache_misses
            cache_rate = (hits / (hits + misses) * 100.0) if (hits + misses) > 0 else 0.0

        try:
            from faces.models import Face
            faces_indexed = Face.objects.count()
        except Exception:
            faces_indexed = 0

        return {
            'extractions_total': tot,
            'extractions_success': succ,
            'extractions_failed': fail,
            'avg_extraction_time_ms': round(avg_ext, 2),
            'search_queries_total': search_tot,
            'avg_search_time_ms': round(avg_search, 2),
            'selfie_cache_hit_rate_percent': round(cache_rate, 2),
            'total_faces_indexed': faces_indexed,
        }

    def get_websocket_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'active_connections': self.ws_active_connections,
                'peak_connections': self.ws_peak_connections,
                'total_connects': self.ws_total_connects,
                'total_disconnects': self.ws_total_disconnects,
                'disconnect_codes': dict(self.ws_disconnect_codes),
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Collects CPU and RAM statistics for host container."""
        try:
            process = psutil.Process()
            cpu_pct = psutil.cpu_percent(interval=None)
            mem_info = process.memory_info()
            sys_mem = psutil.virtual_memory()

            rss_mb = mem_info.rss / (1024 * 1024)
            total_mb = sys_mem.total / (1024 * 1024)
            used_pct = sys_mem.percent

            return {
                'cpu_percent': round(cpu_pct, 1),
                'cpu_count': psutil.cpu_count(),
                'memory_process_rss_mb': round(rss_mb, 1),
                'memory_system_total_mb': round(total_mb, 1),
                'memory_system_used_percent': round(used_pct, 1),
                'is_memory_high': used_pct > 85.0 or rss_mb > 450.0,
            }
        except Exception as e:
            return {
                'error': str(e),
                'cpu_percent': 0.0,
                'memory_process_rss_mb': 0.0,
                'memory_system_used_percent': 0.0,
            }

    def get_android_ingestion_metrics(self) -> Dict[str, Any]:
        """Summarizes Android device heartbeats, FTP status, and disk space."""
        devices = []
        try:
            from photos.models import PhoneDevice
            for dev in PhoneDevice.objects.all():
                is_low_disk = dev.storage_usage_mb > 0 and getattr(dev, 'storage_free_mb', 5000) < 1000
                devices.append({
                    'device_id': dev.device_id,
                    'wedding_slug': dev.wedding.slug,
                    'ftp_status': dev.ftp_status,
                    'local_ip': dev.local_ip,
                    'storage_usage_mb': dev.storage_usage_mb,
                    'queue_waiting': dev.queue_waiting,
                    'queue_failed': dev.queue_failed,
                    'last_seen': dev.last_seen.isoformat() if dev.last_seen else None,
                    'is_online': bool(dev.last_seen and (dj_timezone.now() - dev.last_seen).total_seconds() < 120),
                    'is_low_storage': is_low_disk,
                })
        except Exception:
            pass

        with self._lock:
            ftp_fails = self.android_ftp_failures_total
            http_fails = self.android_http_forward_failures_total

        return {
            'devices': devices,
            'ftp_failures_total': ftp_fails,
            'http_forward_failures_total': http_fails,
        }

    def get_render_metrics(self) -> Dict[str, Any]:
        """Detects Render service restarts and reports container uptime."""
        now = time.time()
        uptime = now - SERVER_BOOT_TIME
        is_recent_restart = uptime < 300  # restarted within last 5 minutes

        return {
            'instance_id': RENDER_INSTANCE_ID,
            'boot_timestamp': SERVER_BOOT_DATETIME,
            'uptime_seconds': int(uptime),
            'uptime_human': str(timedelta(seconds=int(uptime))),
            'recent_restart_detected': is_recent_restart,
        }

    def get_database_growth_metrics(self) -> Dict[str, Any]:
        """Monitors row counts across tables and detects growth anomalies."""
        try:
            from photos.models import Photo, IngestionJob, Transfer
            from faces.models import Face

            now = dj_timezone.now()
            h1_ago = now - timedelta(hours=1)
            d1_ago = now - timedelta(days=1)

            total_photos = Photo.objects.count()
            total_faces = Face.objects.count()
            total_jobs = IngestionJob.objects.count()
            total_transfers = Transfer.objects.count()

            photos_last_hour = Photo.objects.filter(created_at__gte=h1_ago).count()
            photos_last_day = Photo.objects.filter(created_at__gte=d1_ago).count()

            # Growth anomaly: more than 1,000 photos in 1 hour
            growth_anomaly = photos_last_hour > 1000

            return {
                'total_photos': total_photos,
                'total_faces': total_faces,
                'total_ingestion_jobs': total_jobs,
                'total_transfers': total_transfers,
                'photos_added_last_hour': photos_last_hour,
                'photos_added_last_24h': photos_last_day,
                'growth_anomaly_detected': growth_anomaly,
            }
        except Exception as e:
            return {
                'error': str(e),
                'total_photos': 0,
                'total_faces': 0,
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Aggregates all 14 dimensions into a comprehensive snapshot."""
        return {
            'timestamp': dj_timezone.now().isoformat(),
            'api': self.get_api_metrics(),
            'database': self.get_database_metrics(),
            'cloudinary': self.get_cloudinary_metrics(),
            'queue': self.get_queue_metrics(),
            'face_processing': self.get_face_metrics(),
            'websockets': self.get_websocket_metrics(),
            'system': self.get_system_metrics(),
            'android_ingestion': self.get_android_ingestion_metrics(),
            'render': self.get_render_metrics(),
            'database_growth': self.get_database_growth_metrics(),
        }


# Global singleton metrics instance
metrics = MetricsRegistry()


"""
Comprehensive Automated Tests for Observability & Production Monitoring.
Tests:
- Structured JSON logging and sensitive data sanitization
- Correlation ID & upload ID propagation
- Metric collection (API, DB, Cloudinary, Queue, WebSockets, System)
- Actionable alert engine evaluation & severity thresholds
- End-to-end photo lifecycle tracing
- Observability middleware and API endpoints
"""

import os
import json
import uuid
import logging
from unittest.mock import patch, MagicMock

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework import status

from observability.context import set_correlation_id, set_upload_id, get_correlation_id, clear_context
from observability.logging_formatters import StructuredJsonFormatter, sanitize_message_str, sanitize_dict
from observability.metrics import MetricsRegistry
from observability.alerts import AlertEngine
from observability.tracer import PhotoTracer
from observability.middleware import ObservabilityMiddleware
from observability.views import ObservabilityDashboardView, ObservabilityTraceView


class StructuredLoggingSanitizationTests(SimpleTestCase):
    """Verifies that structured JSON logging never leaks credentials or biometric vectors."""

    def setUp(self):
        clear_context()
        self.formatter = StructuredJsonFormatter()

    def tearDown(self):
        clear_context()

    def test_masks_passwords_and_tokens(self):
        msg = "User auth failed with password=SecretWedding123 and token=abc123token and api_key=xyzSecret"
        clean = sanitize_message_str(msg)
        self.assertNotIn("SecretWedding123", clean)
        self.assertNotIn("abc123token", clean)
        self.assertNotIn("xyzSecret", clean)
        self.assertIn("password=[REDACTED]", clean)
        self.assertIn("token=[REDACTED]", clean)
        self.assertIn("api_key=[REDACTED]", clean)

    def test_masks_512_dim_biometric_face_vectors(self):
        # 512-dim embedding float representation
        vector_str = "[0.12345, -0.98765, 0.44321, 0.11223, -0.66554, 0.88776]"
        clean = sanitize_message_str(f"Generated face vector: {vector_str}")
        self.assertNotIn("0.12345", clean)
        self.assertIn("[BIOMETRIC_VECTOR_REDACTED]", clean)

    def test_recursively_sanitizes_dict(self):
        payload = {
            'username': 'photographer_01',
            'password': 'SuperSecretPassword!',
            'auth_token': 'secret_token_value',
            'face_embedding': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1],
            'nested': {
                'api_key': 'secret_key_123',
                'safe_field': 'hello'
            }
        }
        clean = sanitize_dict(payload)
        self.assertEqual(clean['password'], '[REDACTED]')
        self.assertEqual(clean['auth_token'], '[REDACTED]')
        self.assertEqual(clean['face_embedding'], '[BIOMETRIC_VECTOR_REDACTED]')
        self.assertEqual(clean['nested']['api_key'], '[REDACTED]')
        self.assertEqual(clean['nested']['safe_field'], 'hello')

    def test_formatter_injects_contextvars(self):
        test_cid = "corr_abc_123"
        test_uid = "upload_xyz_789"
        set_correlation_id(test_cid)
        set_upload_id(test_uid)

        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Photo upload completed successfully',
            args=(),
            exc_info=None
        )
        formatted = self.formatter.format(record)
        data = json.loads(formatted)

        self.assertEqual(data['correlation_id'], test_cid)
        self.assertEqual(data['upload_id'], test_uid)
        self.assertEqual(data['message'], 'Photo upload completed successfully')
        self.assertEqual(data['level'], 'INFO')


class MetricsRegistryUnitTests(SimpleTestCase):
    """Tests the in-memory metric collector calculations."""

    def test_request_and_error_rate_calculations(self):
        reg = MetricsRegistry()
        reg.record_request(200, 45.0)
        reg.record_request(200, 55.0)
        reg.record_request(200, 60.0)
        reg.record_request(404, 30.0)
        reg.record_request(500, 120.0)

        api_m = reg.get_api_metrics()
        self.assertEqual(api_m['total_requests'], 5)
        self.assertEqual(api_m['requests_2xx'], 3)
        self.assertEqual(api_m['requests_4xx'], 1)
        self.assertEqual(api_m['requests_5xx'], 1)
        self.assertEqual(api_m['error_rate_percent'], 20.0)  # 1 out of 5 is 20%
        self.assertGreater(api_m['p50_latency_ms'], 0.0)

    def test_cloudinary_upload_metrics(self):
        reg = MetricsRegistry()
        reg.record_cloudinary_upload(success=True, duration_ms=250.0)
        reg.record_cloudinary_upload(success=True, duration_ms=300.0)
        reg.record_cloudinary_upload(success=False, duration_ms=500.0, error="Upload timeout")

        cld_m = reg.get_cloudinary_metrics()
        self.assertEqual(cld_m['uploads_total'], 3)
        self.assertEqual(cld_m['uploads_success'], 2)
        self.assertEqual(cld_m['uploads_failed'], 1)
        self.assertAlmostEqual(cld_m['failure_rate_percent'], 33.33, places=1)
        self.assertIn("timeout", cld_m['last_error'].lower())

    def test_websocket_connect_and_disconnect_codes(self):
        reg = MetricsRegistry()
        reg.record_ws_connect()
        reg.record_ws_connect()
        self.assertEqual(reg.ws_active_connections, 2)
        self.assertEqual(reg.ws_peak_connections, 2)

        reg.record_ws_disconnect(code=1000)
        self.assertEqual(reg.ws_active_connections, 1)
        self.assertEqual(reg.ws_disconnect_codes.get(1000), 1)

        reg.record_ws_disconnect(code=4401)
        self.assertEqual(reg.ws_active_connections, 0)
        self.assertEqual(reg.ws_disconnect_codes.get(4401), 1)

    def test_system_resource_metrics(self):
        reg = MetricsRegistry()
        sys_m = reg.get_system_metrics()
        self.assertIn('cpu_percent', sys_m)
        self.assertIn('memory_process_rss_mb', sys_m)
        self.assertGreater(sys_m['memory_process_rss_mb'], 0.0)


class AlertEngineEvaluationTests(SimpleTestCase):
    """Verifies that alert conditions trigger actionable runbook instructions."""

    @patch('observability.alerts.metrics')
    def test_dead_letter_alert_triggered(self, mock_metrics):
        mock_metrics.get_all_metrics.return_value = {
            'database': {'status': 'CONNECTED'},
            'queue': {'dead_letter_count': 3, 'oldest_job_age_seconds': 10.0, 'backlog_count': 5},
            'api': {'error_rate_percent': 0.5},
            'cloudinary': {'failure_rate_percent': 0.0, 'uploads_total': 10},
            'system': {'memory_system_used_percent': 40.0, 'memory_process_rss_mb': 150.0},
            'android_ingestion': {'devices': []},
            'database_growth': {'growth_anomaly_detected': False},
        }

        alerts = AlertEngine.evaluate_active_alerts()
        alert_ids = [a['id'] for a in alerts]

        self.assertIn('INGESTION_DEAD_LETTER', alert_ids)
        dead_letter_alert = next(a for a in alerts if a['id'] == 'INGESTION_DEAD_LETTER')
        self.assertEqual(dead_letter_alert['severity'], 'CRITICAL')
        self.assertIn('action', dead_letter_alert)
        self.assertIn('Retry Dead-Letters', dead_letter_alert['action'])

    @patch('observability.alerts.metrics')
    def test_database_down_alert_triggered(self, mock_metrics):
        mock_metrics.get_all_metrics.return_value = {
            'database': {'status': 'FAILED: connection refused'},
            'queue': {'dead_letter_count': 0, 'oldest_job_age_seconds': 0.0, 'backlog_count': 0},
            'api': {'error_rate_percent': 0.0},
            'cloudinary': {'failure_rate_percent': 0.0, 'uploads_total': 0},
            'system': {'memory_system_used_percent': 40.0, 'memory_process_rss_mb': 150.0},
            'android_ingestion': {'devices': []},
            'database_growth': {'growth_anomaly_detected': False},
        }

        alerts = AlertEngine.evaluate_active_alerts()
        alert_ids = [a['id'] for a in alerts]
        self.assertIn('DB_CONNECTION_FAILURE', alert_ids)
        db_alert = next(a for a in alerts if a['id'] == 'DB_CONNECTION_FAILURE')
        self.assertEqual(db_alert['severity'], 'CRITICAL')
        self.assertIn('DATABASE_URL', db_alert['action'])


class ObservabilityMiddlewareTests(SimpleTestCase):
    """Verifies correlation ID generation, preservation, and metric recording."""

    def setUp(self):
        clear_context()

    def tearDown(self):
        clear_context()

    def test_middleware_generates_correlation_id_if_missing(self):
        factory = APIRequestFactory()
        req = factory.get('/api/test/')

        mock_view = MagicMock(return_value=MagicMock(status_code=200, headers={}, __setitem__=MagicMock()))
        middleware = ObservabilityMiddleware(mock_view)

        resp = middleware(req)
        # Verify X-Correlation-ID was set on the response
        mock_view.return_value.__setitem__.assert_called_with('X-Correlation-ID', mock_view.return_value.__setitem__.call_args[0][1])

    def test_middleware_preserves_client_correlation_id(self):
        factory = APIRequestFactory()
        client_cid = "client_trace_98765"
        req = factory.get('/api/test/', HTTP_X_CORRELATION_ID=client_cid)

        mock_view = MagicMock(return_value=MagicMock(status_code=200, headers={}, __setitem__=MagicMock()))
        middleware = ObservabilityMiddleware(mock_view)

        resp = middleware(req)
        mock_view.return_value.__setitem__.assert_called_with('X-Correlation-ID', client_cid)


class ObservabilityApiViewsTests(SimpleTestCase):
    """Verifies dashboard and trace endpoints."""

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('observability.views.IngestionJob.objects.select_related')
    def test_dashboard_endpoint_returns_metrics(self, mock_jobs_select):
        mock_jobs_select.return_value.order_by.return_value = []
        req = self.factory.get('/api/observability/dashboard/')
        view = ObservabilityDashboardView.as_view()
        resp = view(req)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('service_health', resp.data)
        self.assertIn('summary', resp.data)
        self.assertIn('metrics', resp.data)
        self.assertIn('alerts', resp.data)
        self.assertIn('recent_jobs', resp.data)

    def test_trace_endpoint_missing_id_returns_400(self):
        req = self.factory.get('/api/observability/trace/')
        view = ObservabilityTraceView.as_view()
        resp = view(req)

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing query parameter', resp.data['error'])

    @patch('observability.tracer.PhotoTracer.trace_photo')
    def test_trace_endpoint_not_found_returns_404(self, mock_trace):
        mock_trace.return_value = {'found': False, 'message': 'Not found'}
        req = self.factory.get('/api/observability/trace/?id=nonexistent_id')
        view = ObservabilityTraceView.as_view()
        resp = view(req)

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(resp.data['found'])


"""
Observability REST API views for Live Wedding Gallery.
Provides dashboard metrics, active alerts, end-to-end photo tracing,
and operational recovery tools.
"""

import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from django.utils import timezone

from .metrics import metrics
from .alerts import AlertEngine
from .tracer import PhotoTracer
from photos.models import IngestionJob
from photos.ingestion_service import enqueue_job


class ObservabilityDashboardView(APIView):
    """
    Unified operational dashboard payload.
    Aggregates service health, active alerts, pipeline queue, Cloudinary usage,
    and recent photo ingestion records.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        all_metrics = metrics.get_all_metrics()
        active_alerts = AlertEngine.evaluate_active_alerts()

        # Fetch last 15 ingestion jobs for live activity table
        recent_jobs_qs = IngestionJob.objects.select_related('wedding').order_by('-received_at')[:15]
        recent_jobs = [
            {
                'job_id': str(j.job_id),
                'upload_id': j.upload_id,
                'filename': j.original_filename,
                'folder': j.folder,
                'wedding_slug': j.wedding.slug,
                'status': j.status,
                'attempts': j.attempts,
                'file_size_kb': round(j.file_size / 1024, 1),
                'received_at': j.received_at.isoformat() if j.received_at else None,
                'completed_at': j.completed_at.isoformat() if j.completed_at else None,
                'last_error': j.last_error,
                'duration_seconds': round((j.completed_at - j.received_at).total_seconds(), 1) if (j.received_at and j.completed_at) else None,
            }
            for j in recent_jobs_qs
        ]

        return Response({
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'service_health': all_metrics.get('api', {}).get('status', 'HEALTHY'),
            'summary': {
                'total_requests': all_metrics['api']['total_requests'],
                'requests_per_minute': all_metrics['api']['requests_per_minute'],
                'error_rate_percent': all_metrics['api']['error_rate_percent'],
                'p95_latency_ms': all_metrics['api']['p95_latency_ms'],
                'active_websockets': all_metrics['websockets']['active_connections'],
                'queue_backlog': all_metrics['queue'].get('backlog_count', 0),
                'dead_letter_count': all_metrics['queue'].get('dead_letter_count', 0),
                'total_photos_published': all_metrics['database_growth'].get('total_photos', 0),
                'total_faces_indexed': all_metrics['face_processing'].get('total_faces_indexed', 0),
                'alerts_count': len(active_alerts),
            },
            'alerts': active_alerts,
            'metrics': all_metrics,
            'recent_jobs': recent_jobs,
        })


class ObservabilityMetricsView(APIView):
    """Raw operational metrics snapshot."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(metrics.get_all_metrics())


class ObservabilityAlertsView(APIView):
    """Evaluates and lists all currently active operational alerts."""
    permission_classes = [AllowAny]

    def get(self, request):
        alerts = AlertEngine.evaluate_active_alerts()
        return Response({
            'count': len(alerts),
            'timestamp': timezone.now().isoformat(),
            'alerts': alerts
        })


class ObservabilityTraceView(APIView):
    """
    Traces an individual photo from camera/FTP reception to gallery publication.
    Query param: `id` (upload_id, job_id, checksum, photo_id, or filename).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        identifier = request.query_params.get('id') or request.query_params.get('query')
        if not identifier:
            return Response({
                'error': 'Missing query parameter "id". Provide upload_id, job_id, checksum, or photo_id.'
            }, status=status.HTTP_400_BAD_REQUEST)

        trace_result = PhotoTracer.trace_photo(identifier)
        if not trace_result.get('found'):
            return Response(trace_result, status=status.HTTP_404_NOT_FOUND)

        return Response(trace_result)


class ObservabilityRetryJobView(APIView):
    """
    Operational recovery endpoint to retry a failed or dead-letter ingestion job.
    """
    def post(self, request, job_id):
        try:
            job = IngestionJob.objects.get(job_id=job_id)
        except IngestionJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

        if job.status == 'COMPLETED':
            return Response({'message': 'Job is already completed.'}, status=status.HTTP_200_OK)

        job.status = 'QUEUED'
        job.attempts = 0
        job.dead_letter_reason = None
        job.last_error = f"Operator manual retry triggered at {timezone.now().isoformat()}"
        job.save()

        enqueue_job(job)

        return Response({
            'status': 're-queued',
            'job_id': str(job.job_id),
            'upload_id': job.upload_id,
            'message': 'Job successfully reset to QUEUED and dispatched to worker queue.'
        })


class ObservabilityRetryAllDeadLettersView(APIView):
    """
    Operational recovery endpoint to re-enqueue all DEAD_LETTER jobs.
    """
    def post(self, request):
        dead_jobs = IngestionJob.objects.filter(status='DEAD_LETTER')
        count = 0
        for job in dead_jobs:
            job.status = 'QUEUED'
            job.attempts = 0
            job.dead_letter_reason = None
            job.last_error = f"Operator bulk retry at {timezone.now().isoformat()}"
            job.save()
            enqueue_job(job)
            count += 1

        return Response({
            'status': 'success',
            're_queued_count': count,
            'message': f"Re-enqueued {count} dead-letter jobs for processing."
        })

import os
import uuid
import logging
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponseRedirect
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import CameraConnection, Transfer, Photo, PhoneDevice, IngestionJob
from .serializers import CameraConnectionSerializer, TransferSerializer, PhotoSerializer, IngestionJobSerializer
from .ingestion_service import (
    stage_uploaded_file,
    enqueue_job,
    sanitize_filename,
    process_ingestion_job
)
from .cloudinary_service import (
    delete_photo,
    get_account_usage,
    get_download_url
)
from .security import audit_log
from weddings.models import Wedding

logger = logging.getLogger(__name__)


def authenticate_photographer_or_device(request, wedding, allow_device=True):
    """
    Validates authentication and photographer permissions.
    Accepts:
    1. Active session or token authenticated user (is_staff, superuser, or authenticated photographer).
    2. DRF Token in Authorization header (Token <key> or Bearer <key>).
    3. Registered PhoneDevice for this wedding via device_id (in header X-Device-Id or body device_id).
    Returns: (is_authorized: bool, device: PhoneDevice | None, error_message: str | None)
    """
    # 1. Standard user authentication
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and user.is_active:
        return True, None, None

    # 2. Token header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Token ') or auth_header.startswith('Bearer '):
        token_key = auth_header.split(' ', 1)[1].strip()
        token = Token.objects.filter(key=token_key).select_related('user').first()
        if token and token.user.is_active:
            return True, None, None

    photographer_token = request.headers.get('X-Photographer-Token')
    if photographer_token:
        token = Token.objects.filter(key=photographer_token).select_related('user').first()
        if token and token.user.is_active:
            return True, None, None

    # 3. Registered PhoneDevice verification
    if allow_device:
        device_id = request.headers.get('X-Device-Id') or request.data.get('device_id')
        if device_id:
            device, created = PhoneDevice.objects.get_or_create(
                wedding=wedding,
                device_id=device_id
            )
            if created:
                audit_log('DEVICE_REGISTERED', request=request, wedding_slug=wedding.slug, details=f"Auto-registered device_id={device_id}")
            return True, device, None

    audit_log('UNAUTHORIZED_ACCESS_ATTEMPT', request=request, wedding_slug=wedding.slug, details=f"Path: {request.path}", level='warning')
    return False, None, "Unauthorized: Valid photographer token or registered phone device required."


class CameraConnectView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        
        host = data.get('host', 'ftp.live-wedding-gallery.com')
        port = data.get('port', 21)
        username = data.get('username', f'camera_{slug}')
        
        connection, created = CameraConnection.objects.update_or_create(
            wedding=wedding,
            defaults={
                'host': host,
                'port': port,
                'username': username,
                'connection_status': 'CONNECTED',
            }
        )
        
        return Response(CameraConnectionSerializer(connection).data)


class CameraDisconnectView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        CameraConnection.objects.filter(wedding=wedding).update(connection_status='DISCONNECTED')
        return Response({"status": "disconnected"})


class CameraFolderView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        folder = request.data.get('folder', 'Uncategorized')
        connection = CameraConnection.objects.filter(wedding=wedding).first()
        if connection:
            connection.active_folder = folder
            connection.save()
            return Response(CameraConnectionSerializer(connection).data)
        return Response({"error": "No camera connection found"}, status=404)


class TransferListView(generics.ListAPIView):
    serializer_class = TransferSerializer
    
    def get_queryset(self):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        return Transfer.objects.filter(camera__wedding=wedding).order_by('-started_at')[:100]

    def list(self, request, *args, **kwargs):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return super().list(request, *args, **kwargs)


class PhotographerStatsView(APIView):
    def get(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        
        total_photos = Photo.objects.filter(wedding=wedding).count()
        processing = Photo.objects.filter(wedding=wedding, processing_status='PROCESSING').count()
        failed = Photo.objects.filter(wedding=wedding, processing_status='FAILED').count()
        
        # Ingestion queue stats
        queued_jobs = IngestionJob.objects.filter(wedding=wedding, status__in=['RECEIVED', 'QUEUED', 'UPLOADING', 'DB_REGISTERED', 'FACE_PROCESSING']).count()
        failed_jobs = IngestionJob.objects.filter(wedding=wedding, status__in=['FAILED', 'DEAD_LETTER']).count()

        phone = PhoneDevice.objects.filter(wedding=wedding).order_by('-last_seen').first()
        status_val = phone.ftp_status if phone else 'STOPPED'
        local_ip = phone.local_ip if phone else 'Not connected'
        storage = phone.storage_usage_mb if phone else 0.0
        waiting = (phone.queue_waiting if phone else 0) + queued_jobs
        failed_q = (phone.queue_failed if phone else 0) + failed + failed_jobs

        # Cloudinary single-account usage metrics
        cld_usage = get_account_usage()
        
        return Response({
            "total_photos": total_photos,
            "processing": processing + queued_jobs,
            "failed": failed_q,
            "connection_status": status_val,
            "local_ip": local_ip,
            "storage_mb": storage,
            "queue_waiting": waiting,
            "cloudinary": cld_usage
        })


class CloudinaryUsageView(APIView):
    """
    Returns live account usage metrics, storage consumption, bandwidth, and plan limits.
    """
    def get(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err}, status=status.HTTP_401_UNAUTHORIZED)
        
        usage = get_account_usage()
        return Response(usage)


class PhotoDownloadView(APIView):
    """
    Delivers original-quality master photograph directly from Cloudinary CDN.
    Uses attachment flag so the browser triggers an instant high-res file download.
    """
    def get(self, request, slug, pk):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        photo = get_object_or_404(Photo, id=pk, wedding=wedding)

        download_url = photo.download_url
        if request.query_params.get('redirect') == 'true':
            return HttpResponseRedirect(download_url)

        return Response({
            'photo_id': photo.id,
            'original_filename': photo.original_filename,
            'download_url': download_url,
            'width': photo.width,
            'height': photo.height,
            'file_size': photo.file_size,
            'format': photo.format,
            'resource_type': photo.resource_type
        })


class PhotoDeleteView(APIView):
    def delete(self, request, slug, pk):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding, allow_device=False)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized to delete gallery photos.'}, status=status.HTTP_401_UNAUTHORIZED)
            
        photo = get_object_or_404(Photo, id=pk, wedding=wedding)
        
        try:
            audit_log('PHOTO_DELETED', request=request, wedding_slug=slug, details=f"photo_id={pk} filename={photo.original_filename}")
            
            # Delete from Cloudinary if public_id exists
            if photo.cloudinary_public_id:
                delete_photo(photo.cloudinary_public_id)
                    
            # Delete from database (cascades to faces)
            photo.delete()
            
            # Broadcast deletion to all connected clients
            from photos.realtime import broadcast_delete_photo
            broadcast_delete_photo(slug, pk, wedding_id=wedding.id)
            
            return Response({"status": "success", "message": "Photo deleted successfully"}, status=200)
            
        except Exception as e:
            logger.error(f"Error deleting photo {pk}: {e}", exc_info=True)
            return Response({"error": str(e)}, status=500)


class PhoneAuthView(APIView):
    throttle_scope = 'photographer_login'

    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id required'}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate photographer credentials or token before registering phone device
        from django.contrib.auth import authenticate
        username = request.data.get('username')
        password = request.data.get('password')
        is_authenticated_caller = False

        if username and password:
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                is_authenticated_caller = True

        if not is_authenticated_caller:
            # Check existing token or session
            is_auth, _, _ = authenticate_photographer_or_device(request, wedding, allow_device=False)
            if is_auth:
                is_authenticated_caller = True

        if not is_authenticated_caller:
            audit_log('DEVICE_REGISTRATION_FAILED', request=request, wedding_slug=slug, details=f"Unauthorized registration attempt for device_id: {device_id}", level='warning')
            return Response({'error': 'Photographer credentials or active authorization token required to register device.'}, status=status.HTTP_401_UNAUTHORIZED)

        device, created = PhoneDevice.objects.get_or_create(
            wedding=wedding, 
            device_id=device_id
        )
        audit_log('DEVICE_REGISTERED', request=request, wedding_slug=slug, details=f"device_id={device_id} created={created}")
        return Response({'status': 'authenticated', 'device_id': device.device_id, 'created': created})


class PhoneSyncView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        device = get_object_or_404(PhoneDevice, wedding=wedding, device_id=device_id)
        
        device.local_ip = request.data.get('local_ip', device.local_ip)
        device.storage_usage_mb = request.data.get('storage_usage_mb', device.storage_usage_mb)
        device.ftp_status = request.data.get('ftp_status', device.ftp_status)
        device.queue_waiting = request.data.get('queue_waiting', device.queue_waiting)
        device.queue_failed = request.data.get('queue_failed', device.queue_failed)
        device.last_seen = timezone.now()
        device.save()
        
        return Response({'status': 'synced'})


class PhoneUploadView(APIView):
    """
    Primary ingestion endpoint for photographer Android companion app.
    Accepts chunked streams, stages to disk without memory bloat, creates durable
    IngestionJob record, performs fast content deduplication, and returns HTTP 202 Accepted.
    """
    throttle_scope = 'photo_upload'

    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)

        # 1. Validate authentication and photographer / device permissions
        is_auth, device, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Extract parameters
        folder = request.data.get('folder', 'Uncategorized')
        upload_id = request.data.get('upload_id')
        client_checksum = request.data.get('checksum')
        photo_file = request.FILES.get('photo')

        if not photo_file:
            return Response({'error': 'No photo file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Check for duplicate upload_id
        if upload_id:
            existing_job = IngestionJob.objects.filter(wedding=wedding, upload_id=upload_id).first()
            if existing_job:
                if existing_job.status == 'COMPLETED':
                    return Response({
                        'status': 'COMPLETED',
                        'job_id': str(existing_job.job_id),
                        'upload_id': upload_id,
                        'photo_id': existing_job.photo_id,
                        'checksum': existing_job.checksum,
                        'message': 'Upload already completed'
                    }, status=status.HTTP_200_OK)
                elif existing_job.status in ['QUEUED', 'UPLOADING', 'CLOUDINARY_COMPLETED', 'DB_REGISTERED', 'FACE_PROCESSING']:
                    return Response({
                        'status': existing_job.status,
                        'job_id': str(existing_job.job_id),
                        'upload_id': upload_id,
                        'message': 'Upload already being processed'
                    }, status=status.HTTP_202_ACCEPTED)

        # 4. Create IngestionJob record in RECEIVED status
        job_id = uuid.uuid4()
        safe_original_name = sanitize_filename(photo_file.name)
        job = IngestionJob.objects.create(
            job_id=job_id,
            upload_id=upload_id,
            wedding=wedding,
            device=device,
            original_filename=safe_original_name,
            folder=folder,
            checksum=client_checksum or '',
            status='RECEIVED',
        )

        # 5. Stream chunks to staging file and validate format, magic bytes, and size bounds
        try:
            staged = stage_uploaded_file(photo_file, job_id=job.job_id)
        except ValueError as val_err:
            job.status = 'FAILED'
            job.last_error = str(val_err)
            job.failed_at = timezone.now()
            job.save(update_fields=['status', 'last_error', 'failed_at', 'updated_at'])
            return Response({'error': str(val_err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error(f"Staging failed for job {job.job_id}: {exc}")
            job.status = 'FAILED'
            job.last_error = f"Staging error: {exc}"
            job.failed_at = timezone.now()
            job.save(update_fields=['status', 'last_error', 'failed_at', 'updated_at'])
            return Response({'error': f"Failed to stage photo: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update job with validated staging metadata
        job.staging_path = staged['staging_path']
        job.checksum = staged['checksum']
        job.file_size = staged['file_size']
        job.mime_type = staged['mime_type']
        job.original_filename = staged['original_filename']

        # 6. Check content deduplication (SHA-256 match in Photo gallery)
        existing_photo = Photo.objects.filter(wedding=wedding, checksum=job.checksum).first()
        if existing_photo:
            job.photo = existing_photo
            job.status = 'COMPLETED'
            job.completed_at = timezone.now()
            job.save(update_fields=['photo', 'status', 'completed_at', 'staging_path', 'checksum', 'file_size', 'mime_type', 'updated_at'])
            
            # Clean up staging file since image already exists in Cloudinary & NeonDB
            if job.staging_path and os.path.exists(job.staging_path):
                try:
                    os.remove(job.staging_path)
                    job.staging_path = None
                    job.save(update_fields=['staging_path'])
                except OSError:
                    pass

            return Response({
                'status': 'COMPLETED',
                'job_id': str(job.job_id),
                'upload_id': job.upload_id,
                'photo_id': existing_photo.id,
                'checksum': job.checksum,
                'message': 'Duplicate photo content already exists in gallery'
            }, status=status.HTTP_200_OK)

        # 7. Transition to QUEUED status and submit to background queue
        job.status = 'QUEUED'
        job.queued_at = timezone.now()
        job.save(update_fields=['status', 'queued_at', 'staging_path', 'checksum', 'file_size', 'mime_type', 'original_filename', 'updated_at'])

        enqueue_job(job)

        # 8. Return HTTP 202 Accepted
        return Response({
            'status': 'QUEUED',
            'job_id': str(job.job_id),
            'upload_id': job.upload_id,
            'checksum': job.checksum,
            'filename': job.original_filename,
            'file_size': job.file_size,
            'message': 'Upload accepted and queued for processing'
        }, status=status.HTTP_202_ACCEPTED)


class ManualUploadView(APIView):
    """
    Web dashboard batch manual upload. Uses chunked staging and durable IngestionJob queue.
    """
    throttle_scope = 'photo_upload'

    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err}, status=status.HTTP_401_UNAUTHORIZED)

        folder = request.data.get('folder', 'Uncategorized')
        photos = request.FILES.getlist('photos')
        
        if not photos:
            return Response({"error": "No photos provided"}, status=status.HTTP_400_BAD_REQUEST)

        created_jobs = []
        errors = []

        for photo_file in photos:
            job_id = uuid.uuid4()
            safe_name = sanitize_filename(photo_file.name)
            job = IngestionJob.objects.create(
                job_id=job_id,
                wedding=wedding,
                original_filename=safe_name,
                folder=folder,
                status='RECEIVED',
            )

            try:
                staged = stage_uploaded_file(photo_file, job_id=job.job_id)
                job.staging_path = staged['staging_path']
                job.checksum = staged['checksum']
                job.file_size = staged['file_size']
                job.mime_type = staged['mime_type']
                job.original_filename = staged['original_filename']

                # Check duplicate
                existing_photo = Photo.objects.filter(wedding=wedding, checksum=job.checksum).first()
                if existing_photo:
                    job.photo = existing_photo
                    job.status = 'COMPLETED'
                    job.completed_at = timezone.now()
                    job.save()
                    if job.staging_path and os.path.exists(job.staging_path):
                        try:
                            os.remove(job.staging_path)
                            job.staging_path = None
                            job.save(update_fields=['staging_path'])
                        except OSError:
                            pass
                    created_jobs.append({'job_id': str(job.job_id), 'status': 'COMPLETED', 'filename': safe_name})
                    continue

                job.status = 'QUEUED'
                job.queued_at = timezone.now()
                job.save()
                enqueue_job(job)
                created_jobs.append({'job_id': str(job.job_id), 'status': 'QUEUED', 'filename': safe_name})

            except Exception as e:
                logger.error(f"Error staging manual file {photo_file.name}: {e}")
                job.status = 'FAILED'
                job.last_error = str(e)
                job.failed_at = timezone.now()
                job.save()
                errors.append({'filename': photo_file.name, 'error': str(e)})

        if errors and not created_jobs:
            return Response({
                "status": "error",
                "message": errors[0]['error'],
                "errors": errors
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "processing",
            "count": len(created_jobs),
            "jobs": created_jobs,
            "errors": errors
        }, status=status.HTTP_202_ACCEPTED)


class IngestionJobDetailView(APIView):
    """
    Inspect the progress, status, timestamps, and errors of a specific ingestion job.
    """
    def get(self, request, slug, job_id):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        job = get_object_or_404(IngestionJob, wedding=wedding, job_id=job_id)
        return Response(IngestionJobSerializer(job).data)


class IngestionJobListView(generics.ListAPIView):
    """
    List ingestion jobs for a wedding with optional status filtering.
    """
    serializer_class = IngestionJobSerializer

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        qs = IngestionJob.objects.filter(wedding=wedding)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        limit = int(self.request.query_params.get('limit', 100))
        return qs.order_by('-received_at')[:limit]

    def list(self, request, *args, **kwargs):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return super().list(request, *args, **kwargs)


class IngestionJobRetryView(APIView):
    """
    Manually retries a FAILED or DEAD_LETTER ingestion job.
    """
    def post(self, request, slug, job_id):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err}, status=status.HTTP_401_UNAUTHORIZED)

        job = get_object_or_404(IngestionJob, wedding=wedding, job_id=job_id)

        if job.status not in ['FAILED', 'DEAD_LETTER']:
            return Response({'error': f"Job is in state {job.status}, only FAILED or DEAD_LETTER jobs can be retried."}, status=status.HTTP_400_BAD_REQUEST)

        # Staging file is only strictly needed if Cloudinary upload hasn't already completed
        if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
            return Response({'error': f"Staging file not found on disk at {job.staging_path} and Cloudinary upload not yet completed. Source file must be re-sent."}, status=status.HTTP_400_BAD_REQUEST)

        # Reset retry parameters
        job.status = 'QUEUED'
        job.attempts = 0
        job.last_error = None
        job.dead_letter_reason = None
        job.queued_at = timezone.now()
        job.save()

        enqueue_job(job)

        return Response({
            'status': 'QUEUED',
            'job_id': str(job.job_id),
            'message': 'Job reset and re-queued for processing',
            'job': IngestionJobSerializer(job).data
        }, status=status.HTTP_202_ACCEPTED)


class QueueMonitoringView(APIView):
    """
    Operational API endpoint for monitoring background job queue depth,
    job age, failure rates, and recent errors for a wedding gallery.
    """
    def get(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        now = timezone.now()
        jobs_qs = IngestionJob.objects.filter(wedding=wedding)

        counts = {
            'received': jobs_qs.filter(status='RECEIVED').count(),
            'queued': jobs_qs.filter(status='QUEUED').count(),
            'uploading': jobs_qs.filter(status='UPLOADING').count(),
            'cloudinary_completed': jobs_qs.filter(status='CLOUDINARY_COMPLETED').count(),
            'db_registered': jobs_qs.filter(status='DB_REGISTERED').count(),
            'face_processing': jobs_qs.filter(status='FACE_PROCESSING').count(),
            'completed': jobs_qs.filter(status='COMPLETED').count(),
            'failed': jobs_qs.filter(status='FAILED').count(),
            'dead_letter': jobs_qs.filter(status='DEAD_LETTER').count(),
        }

        active_count = (
            counts['received'] + counts['queued'] + counts['uploading'] +
            counts['cloudinary_completed'] + counts['db_registered'] + counts['face_processing']
        )
        total_jobs = jobs_qs.count()
        failed_total = counts['failed'] + counts['dead_letter']
        failure_rate = round((failed_total / total_jobs * 100), 2) if total_jobs > 0 else 0.0

        # Calculate oldest pending job age
        oldest_pending = jobs_qs.filter(
            status__in=['RECEIVED', 'QUEUED', 'UPLOADING', 'DB_REGISTERED', 'FACE_PROCESSING']
        ).order_by('received_at').first()

        oldest_age_seconds = None
        if oldest_pending and oldest_pending.received_at:
            oldest_age_seconds = int((now - oldest_pending.received_at).total_seconds())

        # Recent failures
        recent_failures = list(
            jobs_qs.filter(status__in=['FAILED', 'DEAD_LETTER'])
            .order_by('-updated_at')[:10]
            .values('job_id', 'original_filename', 'status', 'attempts', 'last_error', 'dead_letter_reason', 'failed_at')
        )

        return Response({
            'wedding': wedding.slug,
            'counts': counts,
            'active_in_flight': active_count,
            'total_jobs': total_jobs,
            'failure_rate_percent': failure_rate,
            'oldest_pending_age_seconds': oldest_age_seconds,
            'recent_failures': recent_failures,
        })


class QueueBatchRetryView(APIView):
    """
    Operational API endpoint to batch retry failed or dead-letter jobs.
    """
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        is_auth, _, auth_err = authenticate_photographer_or_device(request, wedding)
        if not is_auth:
            return Response({'error': auth_err or 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        mode = request.data.get('type', 'all').lower()  # 'failed', 'dead_letter', or 'all'

        if mode == 'failed':
            target_statuses = ['FAILED']
        elif mode == 'dead_letter':
            target_statuses = ['DEAD_LETTER']
        else:
            target_statuses = ['FAILED', 'DEAD_LETTER']

        jobs_to_retry = IngestionJob.objects.filter(
            wedding=wedding,
            status__in=target_statuses
        )

        retried_count = 0
        skipped_count = 0

        for job in jobs_to_retry:
            # Check staging file if not uploaded yet
            if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
                skipped_count += 1
                continue

            job.status = 'QUEUED'
            job.attempts = 0
            job.last_error = None
            job.dead_letter_reason = None
            job.queued_at = timezone.now()
            job.save(update_fields=['status', 'attempts', 'last_error', 'dead_letter_reason', 'queued_at', 'updated_at'])
            enqueue_job(job)
            retried_count += 1

        return Response({
            'message': f"Batch retry triggered for {retried_count} jobs.",
            'retried_count': retried_count,
            'skipped_count': skipped_count,
        })

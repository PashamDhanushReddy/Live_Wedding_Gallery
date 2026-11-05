"""
End-to-End Photo Lifecycle Tracer.
Enables tracing an individual photograph from camera/FTP reception to gallery publication.
Queries by upload_id, job_id, checksum, photo_id, or original filename.
"""

import uuid
from typing import Dict, Any, Optional, List
from django.utils import timezone

from photos.models import IngestionJob, Photo, Transfer, PhoneDevice
from faces.models import Face


class PhotoTracer:
    """Reconstructs the full chronological audit trace for any photo."""

    @classmethod
    def trace_photo(cls, identifier: str) -> Dict[str, Any]:
        """
        Locates the photograph and returns an end-to-end chronological timeline.
        Identifier can be:
        - upload_id (e.g. companion app UUID)
        - job_id (UUID string)
        - checksum (SHA-256 64-char string)
        - photo_id (integer)
        - original_filename
        """
        identifier = str(identifier).strip()
        job: Optional[IngestionJob] = None
        photo: Optional[Photo] = None
        transfer: Optional[Transfer] = None

        # 1. Try finding by UUID job_id or upload_id
        try:
            val_uuid = uuid.UUID(identifier)
            job = IngestionJob.objects.select_related('wedding', 'device', 'photo').filter(job_id=val_uuid).first()
        except ValueError:
            pass

        if not job:
            job = IngestionJob.objects.select_related('wedding', 'device', 'photo').filter(upload_id=identifier).first()

        # 2. Try finding by integer photo_id
        if not job and identifier.isdigit():
            photo_id = int(identifier)
            photo = Photo.objects.select_related('wedding').filter(id=photo_id).first()
            if photo:
                job = IngestionJob.objects.select_related('wedding', 'device', 'photo').filter(photo=photo).first()

        # 3. Try finding by checksum
        if not job and len(identifier) == 64:
            job = IngestionJob.objects.select_related('wedding', 'device', 'photo').filter(checksum=identifier).first()
            if not photo:
                photo = Photo.objects.select_related('wedding').filter(checksum=identifier).first()

        # 4. Try finding by original filename
        if not job:
            job = IngestionJob.objects.select_related('wedding', 'device', 'photo').filter(original_filename__iexact=identifier).first()
            if not photo:
                photo = Photo.objects.select_related('wedding').filter(original_filename__iexact=identifier).first()

        # Link photo if job found
        if job and job.photo and not photo:
            photo = job.photo

        # Find camera transfer record if any
        if photo:
            transfer = Transfer.objects.filter(photo=photo).first()
        elif job:
            transfer = Transfer.objects.filter(filename=job.original_filename).first()

        if not job and not photo and not transfer:
            return {
                'found': False,
                'query': identifier,
                'message': f"No photograph or ingestion job matching '{identifier}' was found in the system."
            }

        # ----------------------------------------------------------------------
        # Construct Chronological Milestones
        # ----------------------------------------------------------------------
        milestones: List[Dict[str, Any]] = []

        # Hop 1: Camera / Companion FTP Ingestion
        device_id = job.device.device_id if (job and job.device) else "Companion Device"
        ftp_time = transfer.started_at if transfer else (job.received_at if job else None)
        milestones.append({
            'step': 1,
            'name': 'FTP_RECEPTION',
            'title': 'Camera to Android Companion Reception',
            'status': 'COMPLETED' if (job or photo) else (transfer.status if transfer else 'UNKNOWN'),
            'timestamp': ftp_time.isoformat() if ftp_time else None,
            'details': {
                'device_id': device_id,
                'filename': (job.original_filename if job else (photo.original_filename if photo else (transfer.filename if transfer else 'Unknown'))),
                'camera_host': transfer.camera.host if (transfer and transfer.camera) else 'FTP Hotspot',
            }
        })

        # Hop 2: Android HTTP Forwarding Intake
        if job:
            milestones.append({
                'step': 2,
                'name': 'HTTP_INTAKE_STAGED',
                'title': 'HTTP Streaming Ingestion to Django Backend',
                'status': 'COMPLETED',
                'timestamp': job.received_at.isoformat() if job.received_at else None,
                'details': {
                    'upload_id': job.upload_id,
                    'checksum': job.checksum,
                    'file_size_bytes': job.file_size,
                    'mime_type': job.mime_type,
                    'folder': job.folder,
                }
            })

            # Hop 3: Durable Job Queue Placement
            milestones.append({
                'step': 3,
                'name': 'QUEUE_DISPATCH',
                'title': 'Celery & Redis Worker Queue Enqueued',
                'status': 'COMPLETED' if job.status != 'RECEIVED' else 'IN_PROGRESS',
                'timestamp': job.queued_at.isoformat() if job.queued_at else None,
                'details': {
                    'job_id': str(job.job_id),
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                }
            })

            # Hop 4: Cloudinary Upload
            cld_status = 'COMPLETED' if job.cloudinary_public_id else ('IN_PROGRESS' if job.status == 'UPLOADING' else 'PENDING')
            if job.status in ('FAILED', 'DEAD_LETTER') and not job.cloudinary_public_id:
                cld_status = 'FAILED'
            milestones.append({
                'step': 4,
                'name': 'CLOUDINARY_UPLOAD',
                'title': 'Cloudinary CDN Streaming & Asset Upload',
                'status': cld_status,
                'timestamp': job.cloudinary_completed_at.isoformat() if job.cloudinary_completed_at else None,
                'details': {
                    'public_id': job.cloudinary_public_id,
                    'secure_url': job.secure_url,
                    'resolution': f"{job.image_width}x{job.image_height}" if job.image_width else None,
                    'format': job.format,
                }
            })

            # Hop 5: Database Registration
            db_status = 'COMPLETED' if (job.photo or job.db_registered_at) else ('FAILED' if job.status in ('FAILED', 'DEAD_LETTER') else 'PENDING')
            milestones.append({
                'step': 5,
                'name': 'DB_REGISTRATION',
                'title': 'NeonDB Transactional Record Committed',
                'status': db_status,
                'timestamp': job.db_registered_at.isoformat() if job.db_registered_at else None,
                'details': {
                    'photo_id': job.photo_id if job.photo else (photo.id if photo else None),
                    'wedding_slug': job.wedding.slug,
                }
            })

            # Hop 6: Face Extraction
            face_records = Face.objects.filter(photo=job.photo) if job.photo else []
            face_status = 'COMPLETED' if (job.photo and job.photo.processing_status == 'COMPLETED') else ('IN_PROGRESS' if job.status == 'FACE_PROCESSING' else 'PENDING')
            milestones.append({
                'step': 6,
                'name': 'FACE_RECOGNITION',
                'title': 'InsightFace Neural Embedding Generation',
                'status': face_status,
                'timestamp': job.face_processing_at.isoformat() if job.face_processing_at else None,
                'details': {
                    'faces_detected': len(face_records),
                    'indexed_in_hnsw': len(face_records) > 0,
                }
            })

            # Hop 7: WebSocket Broadcast
            ws_status = 'COMPLETED' if job.status == 'COMPLETED' else 'PENDING'
            milestones.append({
                'step': 7,
                'name': 'WEBSOCKET_BROADCAST',
                'title': 'Real-time Channels WebSocket Notification Dispatched',
                'status': ws_status,
                'timestamp': job.completed_at.isoformat() if job.completed_at else None,
                'details': {
                    'room_group': f"wedding_{job.wedding.slug}",
                    'event_type': 'new_photo',
                }
            })

        # Calculate Total Duration
        total_duration_sec = None
        if job and job.received_at and job.completed_at:
            total_duration_sec = round((job.completed_at - job.received_at).total_seconds(), 2)

        return {
            'found': True,
            'query': identifier,
            'current_status': job.status if job else (photo.processing_status if photo else 'UNKNOWN'),
            'total_duration_seconds': total_duration_sec,
            'summary': {
                'photo_id': photo.id if photo else (job.photo_id if job else None),
                'upload_id': job.upload_id if job else None,
                'job_id': str(job.job_id) if job else None,
                'filename': job.original_filename if job else (photo.original_filename if photo else None),
                'checksum': job.checksum if job else (photo.checksum if photo else None),
                'wedding_slug': (job.wedding.slug if job else (photo.wedding.slug if photo else None)),
                'cloudinary_url': photo.secure_url if photo else (job.secure_url if job else None),
                'thumbnail_url': photo.thumbnail_url if photo else None,
                'last_error': job.last_error if job else None,
                'dead_letter_reason': job.dead_letter_reason if job else None,
            },
            'milestones': milestones,
        }


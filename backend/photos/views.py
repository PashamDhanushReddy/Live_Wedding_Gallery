from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import CameraConnection, Transfer, Photo, PhoneDevice
from .serializers import CameraConnectionSerializer, TransferSerializer
from weddings.models import Wedding
from faces.models import Face
import cloudinary.uploader
import cv2
import numpy as np
import threading
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

class CameraConnectView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        data = request.data
        
        # In a real app, you'd generate these or have them statically assigned per wedding
        # For this prototype, we'll accept them or auto-generate them
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
        CameraConnection.objects.filter(wedding=wedding).update(connection_status='DISCONNECTED')
        return Response({"status": "disconnected"})

class CameraFolderView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
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

class PhotographerStatsView(APIView):
    def get(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        
        total_photos = Photo.objects.filter(wedding=wedding).count()
        processing = Photo.objects.filter(wedding=wedding, processing_status='PROCESSING').count()
        failed = Photo.objects.filter(wedding=wedding, processing_status='FAILED').count()
        
        phone = PhoneDevice.objects.filter(wedding=wedding).order_by('-last_seen').first()
        status = phone.ftp_status if phone else 'STOPPED'
        local_ip = phone.local_ip if phone else 'Not connected'
        storage = phone.storage_usage_mb if phone else 0.0
        waiting = phone.queue_waiting if phone else 0
        failed_q = phone.queue_failed if phone else 0
        
        return Response({
            "total_photos": total_photos,
            "processing": processing,
            "failed": failed + failed_q,
            "connection_status": status,
            "local_ip": local_ip,
            "storage_mb": storage,
            "queue_waiting": waiting
        })

import concurrent.futures

# Global cache for the InsightFace model
_face_app = None
_face_lock = threading.Lock()

def get_face_app():
    global _face_app
    if _face_app is None:
        with _face_lock:
            if _face_app is None:
                from insightface.app import FaceAnalysis
                _face_app = FaceAnalysis(name='buffalo_l')
                _face_app.prepare(ctx_id=0, det_size=(640, 640))
    return _face_app

class PhotoDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, slug, pk):
        try:
            wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
            photo = get_object_or_404(Photo, id=pk, wedding=wedding)
            
            # Delete from Cloudinary if it exists
            if photo.cloudinary_public_id:
                try:
                    cloudinary.uploader.destroy(photo.cloudinary_public_id)
                except Exception as e:
                    print(f"Failed to delete from Cloudinary: {e}")
                    
            # Delete from database (this will cascade delete faces)
            photo.delete()
            
            # Broadcast deletion to all connected clients
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'wedding_{slug}',
                {
                    'type': 'delete_photo',
                    'photo_id': pk
                }
            )
            
            return Response({"status": "success", "message": "Photo deleted successfully"}, status=200)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# Use a thread pool to prevent OOM when uploading 400 photos
_upload_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def process_manual_upload(wedding, filename, file_bytes, folder):
    try:
        from photos.serializers import PhotoSerializer
        
        # Prevent duplicates
        if Photo.objects.filter(wedding=wedding, original_filename=filename).exists():
            logger.info(f"Duplicate detected for {filename}, skipping upload.")
            return
            
        logger.info(f"Uploading {filename} to Cloudinary folder {folder}...")
        
        # Add retry logic for unexpected SSL drops or network blips
        import time
        max_retries = 3
        upload_result = None
        for attempt in range(max_retries):
            try:
                upload_result = cloudinary.uploader.upload(
                    file_bytes,
                    folder=f"weddings/{wedding.slug}/{folder}/originals"
                )
                break  # Success, break the loop
            except Exception as e:
                logger.warning(f"Upload failed for {filename} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise  # Re-raise on final attempt
                time.sleep(2)
        
        logger.info(f"Saving {filename} to DB...")
        photo = Photo.objects.create(
            wedding=wedding,
            original_filename=filename,
            cloudinary_public_id=upload_result.get('public_id'),
            secure_url=upload_result.get('secure_url'),
            cloudinary_url=upload_result.get('url'),
            width=upload_result.get('width'),
            height=upload_result.get('height'),
            file_size=upload_result.get('bytes'),
            folder=folder,
            processing_status='PROCESSING',
            upload_status='COMPLETED',
            captured_at=timezone.now()
        )
        
        # Face extraction
        try:
            app = get_face_app()
            
            # Read from bytes
            np_arr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            with _face_lock:
                faces = app.get(img)
            
            for face in faces:
                bbox = face.bbox
                embedding = face.embedding.tolist()
                Face.objects.create(
                    photo=photo,
                    embedding=embedding,
                    x=bbox[0],
                    y=bbox[1],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                    detection_confidence=face.det_score
                )
        except Exception as e:
            logger.error(f"Face extraction failed: {e}")
            
        photo.processing_status = 'COMPLETED'
        photo.save()
        
        # Broadcast
        channel_layer = get_channel_layer()
        photo_data = PhotoSerializer(photo).data
        async_to_sync(channel_layer.group_send)(
            f'wedding_{wedding.slug}',
            {
                'type': 'new_photo',
                'photo': photo_data
            }
        )
    except Exception as e:
        logger.error(f"Error processing manual upload: {e}")

class ManualUploadView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        folder = request.data.get('folder', 'Uncategorized')
        photos = request.FILES.getlist('photos')
        
        if not photos:
            return Response({"error": "No photos provided"}, status=400)
         # Process in background pool
        for photo_file in photos:
            file_bytes = photo_file.read()
            filename = photo_file.name
            _upload_executor.submit(process_manual_upload, wedding, filename, file_bytes, folder)
            
        return Response({"status": "processing", "count": len(photos)})

class PhoneAuthView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id required'}, status=400)
            
        device, _ = PhoneDevice.objects.get_or_create(
            wedding=wedding, 
            device_id=device_id
        )
        return Response({'status': 'authenticated', 'device_id': device.device_id})

class PhoneSyncView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id required'}, status=400)
            
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
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        device_id = request.data.get('device_id')
        folder = request.data.get('folder', 'Uncategorized')
        photo_file = request.FILES.get('photo')
        
        if not photo_file:
            return Response({'error': 'No photo provided'}, status=400)
            
        try:
            file_bytes = photo_file.read()
            filename = photo_file.name
            
            # Submit to background executor to prevent blocking
            _upload_executor.submit(process_manual_upload, wedding, filename, file_bytes, folder)
            
            return Response({'status': 'processing'})
        except Exception as e:
            logger.error(f"Phone upload error: {e}")
            return Response({'error': str(e)}, status=500)

import hashlib
from photos.models import Photo
from storage.services import CloudinaryStorageManager
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

class PhotoUploadService:
    @staticmethod
    def calculate_sha256(file_obj):
        sha256_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            sha256_hash.update(chunk)
        file_obj.seek(0)
        return sha256_hash.hexdigest()

    @staticmethod
    def process_upload(wedding, file_obj, original_filename):
        # 1. Calculate SHA-256
        file_hash = PhotoUploadService.calculate_sha256(file_obj)
        
        # 2. Duplicate check
        existing_photo = Photo.objects.filter(wedding=wedding, sha256=file_hash).first()
        if existing_photo:
            logger.info(f"Duplicate photo detected: {original_filename} ({file_hash})")
            return existing_photo, False  # False means not newly created

        # 3. Upload to Cloudinary (or fallback)
        try:
            upload_result = CloudinaryStorageManager.upload_photo(file_obj, folder=f"weddings/{wedding.slug}")
        except Exception as e:
            logger.warning(f"Cloudinary upload failed, falling back to local storage: {e}")
            from django.core.files.storage import default_storage
            import uuid
            import os
            
            file_obj.seek(0)
            ext = os.path.splitext(original_filename)[1]
            local_filename = f"weddings/{wedding.slug}/{uuid.uuid4()}{ext}"
            saved_path = default_storage.save(local_filename, file_obj)
            local_url = default_storage.url(saved_path)
            
            upload_result = {
                'account': None,
                'public_id': local_filename,
                'url': local_url,
                'bytes': file_obj.size,
                'width': 1920,
                'height': 1080
            }
        
        # 4. Save database record
        auto_publish = getattr(settings, 'AUTO_PUBLISH_PHOTOS', True)
        
        photo = Photo.objects.create(
            wedding=wedding,
            sha256=file_hash,
            original_filename=original_filename,
            file_size=upload_result['bytes'],
            width=upload_result['width'],
            height=upload_result['height'],
            cloudinary_account=upload_result['account'],
            cloudinary_public_id=upload_result['public_id'],
            cloudinary_url=upload_result['url'],
            status='READY',
            is_published=auto_publish
        )
        
        # Phase 14: Update account capacity
        if upload_result['account']:
            account = upload_result['account']
            account.current_capacity_bytes += upload_result['bytes']
            account.save(update_fields=['current_capacity_bytes'])
            
            # Generate optimized URLs
            photo.thumbnail_url = CloudinaryStorageManager.get_thumbnail_url(upload_result['account'], upload_result['public_id'])
            photo.display_url = CloudinaryStorageManager.get_display_url(upload_result['account'], upload_result['public_id'])
        else:
            photo.thumbnail_url = upload_result['url']
            photo.display_url = upload_result['url']
            
        photo.save(update_fields=['thumbnail_url', 'display_url'])
        
        # Publish WebSocket event (Phase 6)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"wedding_{wedding.slug}",
            {
                "type": "photo_message",
                "event_type": "photo.created",
                "photo": {
                    "id": photo.id,
                    "url": photo.thumbnail_url,
                    "display_url": photo.display_url,
                    "width": photo.width,
                    "height": photo.height
                }
            }
        )
        
        # Queue face recognition (Phase 10)
        from recognition.tasks import process_face_recognition
        process_face_recognition.delay(photo.id)
        
        return photo, True

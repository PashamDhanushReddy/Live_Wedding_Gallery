from celery import shared_task
from photos.models import Photo
from .services import FaceRecognitionService
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_face_recognition(photo_id):
    try:
        photo = Photo.objects.get(id=photo_id)
        FaceRecognitionService.process_photo(photo)
    except Photo.DoesNotExist:
        logger.error(f"Photo {photo_id} not found for face recognition")
    except Exception as e:
        logger.error(f"Error in face recognition task: {e}")

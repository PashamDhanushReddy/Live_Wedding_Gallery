from celery import shared_task
from django.utils import timezone
from .models import Guest
import logging

logger = logging.getLogger(__name__)

@shared_task
def delete_expired_guests():
    now = timezone.now()
    expired_guests = Guest.objects.filter(expires_at__lt=now)
    count = expired_guests.count()
    if count > 0:
        expired_guests.delete()
        logger.info(f"Deleted {count} expired guest sessions for privacy compliance.")

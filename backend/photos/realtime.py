import logging
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

logger = logging.getLogger(__name__)


def invalidate_gallery_cache(wedding_id: int, wedding_slug: str = None, folder: str = None):
    """Purges cached gallery pages and photo counts when photos are added or deleted."""
    if not wedding_id:
        return
    try:
        common_folders = [
            'all', 'All', 'Bride_and_Groom', 'Bride', 'Groom', 'Engagement',
            'Pre-wedding_Shoot', 'Wedding_Day', 'Haldi', 'Before_Wedding_Rituals',
            'Reception', 'Guests', 'Ceremony', 'Family', 'Uncategorized'
        ]
        if folder:
            common_folders.append(str(folder).replace(' ', '_'))
            common_folders.append(str(folder))

        keys_to_delete = []
        for f in set(common_folders):
            keys_to_delete.append(f"wedding_photo_count:{wedding_id}:{f}")
            keys_to_delete.append(f"gallery_p1:{wedding_id}:{f}:25")
            keys_to_delete.append(f"gallery_p1:{wedding_id}:{f}:50")
        if wedding_slug:
            keys_to_delete.append(f"wedding_detail:{wedding_slug}")
        cache.delete_many(keys_to_delete)
        logger.debug(f"Invalidated gallery cache keys for wedding {wedding_id}")
    except Exception as e:
        logger.warning(f"Error invalidating gallery cache: {e}")


def broadcast_new_photo(photo) -> bool:
    """
    Broadcasts a lightweight new_photo event to the wedding's WebSocket room.
    Ensures notifications are sent ONLY after the photo has been registered successfully
    and committed in NeonDB with status COMPLETED.
    Never broadcasts original image files or heavy serialized payloads.
    """
    if not photo:
        logger.warning("broadcast_new_photo called with None photo.")
        return False

    status = getattr(photo, 'processing_status', None)
    if status != 'COMPLETED':
        logger.warning(f"Skipping broadcast: Photo {getattr(photo, 'id', None)} has status '{status}', not COMPLETED.")
        return False

    wedding = getattr(photo, 'wedding', None)
    if not wedding or not getattr(wedding, 'slug', None):
        logger.warning(f"Skipping broadcast: Photo {photo.id} has no valid associated wedding.")
        return False

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer configured; skipping WebSocket broadcast.")
            return False

        try:
            from observability.context import get_correlation_id, get_upload_id
            cid = get_correlation_id()
            uid = get_upload_id()
        except ImportError:
            cid = None
            uid = None

        event = {
            'type': 'new_photo',
            'photo_id': photo.id,
            'wedding_id': wedding.id,
            'wedding_slug': wedding.slug,
            'folder': photo.folder or 'Uncategorized',
            'ai_category': getattr(photo, 'ai_category', None),
            'status': photo.processing_status,
            'created_at': photo.created_at.isoformat() if photo.created_at else None,
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
            'correlation_id': cid,
            'upload_id': uid,
        }

        async_to_sync(channel_layer.group_send)(
            f'wedding_{wedding.slug}',
            event
        )
        # Invalidate cached gallery first page and photo count
        invalidate_gallery_cache(wedding.id, wedding.slug)
        logger.info(f"Broadcasted lightweight new_photo event for photo {photo.id} to wedding_{wedding.slug}")
        return True
    except Exception as e:
        logger.warning(f"Failed to broadcast new_photo event for photo {photo.id}: {e}")
        return False

def broadcast_delete_photo(wedding_slug: str, photo_id: int, wedding_id: int = None) -> bool:
    """
    Broadcasts a lightweight delete_photo event to the wedding's WebSocket room.
    """
    if not wedding_slug or not photo_id:
        return False

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return False

        event = {
            'type': 'delete_photo',
            'photo_id': photo_id,
            'wedding_slug': wedding_slug,
            'wedding_id': wedding_id,
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
        }

        async_to_sync(channel_layer.group_send)(
            f'wedding_{wedding_slug}',
            event
        )
        # Invalidate cached gallery first page and photo count
        invalidate_gallery_cache(wedding_id, wedding_slug)
        logger.info(f"Broadcasted delete_photo event for photo {photo_id} to wedding_{wedding_slug}")
        return True
    except Exception as e:
        logger.warning(f"Failed to broadcast delete_photo event for photo {photo_id}: {e}")
        return False


import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from accounts.models import CloudinaryAccount
from django.conf import settings

logger = logging.getLogger(__name__)

class CloudinaryStorageManager:
    """
    Manages uploads across multiple Cloudinary accounts based on capacity.
    """
    
    @staticmethod
    def get_safe_limit_bytes():
        # Read from settings, default 23GB
        limit_gb = getattr(settings, 'CLOUDINARY_SAFE_LIMIT_GB', 23)
        return int(limit_gb) * 1024 * 1024 * 1024

    @staticmethod
    def select_account(file_size_bytes):
        safe_limit = CloudinaryStorageManager.get_safe_limit_bytes()
        accounts = CloudinaryAccount.objects.filter(is_active=True).order_by('-priority', 'id')
        
        for account in accounts:
            if account.used_bytes + file_size_bytes <= safe_limit:
                return account
        
        logger.error("All Cloudinary accounts are full or inactive.")
        return None

    @staticmethod
    def _configure_cloudinary(account):
        cloudinary.config(
            cloud_name=account.cloud_name,
            api_key=account.api_key,
            api_secret=account.api_secret,
            secure=True
        )

    @staticmethod
    def upload_photo(file_obj, folder="wedding_photos"):
        file_size = file_obj.size
        account = CloudinaryStorageManager.select_account(file_size)
        
        if not account:
            raise Exception("No active Cloudinary account with sufficient capacity.")

        CloudinaryStorageManager._configure_cloudinary(account)
        
        try:
            result = cloudinary.uploader.upload(
                file_obj,
                folder=folder,
                resource_type="image"
            )
            account.used_bytes += result.get('bytes', file_size)
            account.save(update_fields=['used_bytes'])
            
            return {
                'account': account,
                'public_id': result['public_id'],
                'url': result['secure_url'],
                'format': result['format'],
                'width': result['width'],
                'height': result['height'],
                'bytes': result['bytes']
            }
        except Exception as e:
            logger.error(f"Cloudinary upload failed on account {account.name}: {e}")
            raise

    @staticmethod
    def delete_photo(account, public_id):
        CloudinaryStorageManager._configure_cloudinary(account)
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result
        except Exception as e:
            logger.error(f"Failed to delete {public_id} from {account.name}: {e}")
            return False

    @staticmethod
    def get_photo_url(account, public_id, **options):
        CloudinaryStorageManager._configure_cloudinary(account)
        url, _ = cloudinary.utils.cloudinary_url(public_id, **options)
        return url

    @staticmethod
    def get_thumbnail_url(account, public_id):
        return CloudinaryStorageManager.get_photo_url(
            account, public_id, width=400, height=400, crop="fill", format="webp"
        )

    @staticmethod
    def get_display_url(account, public_id):
        return CloudinaryStorageManager.get_photo_url(
            account, public_id, width=1920, height=1080, crop="limit", format="webp"
        )

    @staticmethod
    def health_check(account):
        CloudinaryStorageManager._configure_cloudinary(account)
        try:
            result = cloudinary.api.ping()
            if result.get('status') == 'ok':
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_account_usage(account):
        CloudinaryStorageManager._configure_cloudinary(account)
        try:
            usage = cloudinary.api.usage()
            return usage
        except Exception as e:
            logger.error(f"Failed to get usage for {account.name}: {e}")
            return None

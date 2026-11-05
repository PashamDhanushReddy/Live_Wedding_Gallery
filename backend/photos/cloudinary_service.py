"""
Centralized Cloudinary Service for Live Wedding Gallery.

STRICT POLICY: Single Cloudinary account only. No multiple accounts, rotation, or fallback accounts.
Consistently configured via:
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET
"""

import os
import re
import time
import socket
import logging
from datetime import datetime
from urllib.parse import quote

import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Ensure single Cloudinary account is configured
_is_configured = False

def configure_cloudinary():
    """Configures Cloudinary with the single authorized account."""
    global _is_configured
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    if not all([cloud_name, api_key, api_secret]):
        logger.error(
            "Cloudinary credentials missing! Please ensure CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET are set."
        )
        return False

    cloudinary.config(
        cloud_name=cloud_name.strip(),
        api_key=api_key.strip(),
        api_secret=api_secret.strip(),
        secure=True
    )
    _is_configured = True
    return True


# Configure on import
configure_cloudinary()


def sanitize_folder_name(folder: str) -> str:
    """Sanitize folder segment for Cloudinary public ID hierarchy."""
    if not folder or folder.strip().lower() in ['uncategorized', 'none', '']:
        return 'originals'
    clean = re.sub(r'[^a-zA-Z0-9_-]', '_', folder.strip())
    return clean[:50]


def generate_public_id(wedding_slug: str, folder: str, checksum: str, upload_date=None) -> str:
    """
    Generates a unique, predictable Cloudinary public ID organized by wedding, folder, and upload date.
    Structure: weddings/{wedding_slug}/{folder}/{YYYY-MM-DD}/{checksum[:16]}
    Because the checksum is included, uploads are naturally idempotent on retries.
    """
    clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', wedding_slug or 'default')
    clean_folder = sanitize_folder_name(folder)
    
    if upload_date is None:
        upload_date = timezone.now()
    if hasattr(upload_date, 'strftime'):
        date_str = upload_date.strftime('%Y-%m-%d')
    else:
        date_str = str(upload_date)[:10]

    short_hash = (checksum or 'photo')[:16]
    return f"weddings/{clean_slug}/{clean_folder}/{date_str}/{short_hash}"


# ==============================================================================
# Dynamic Delivery Transformations (Direct Cloudinary CDN)
# ==============================================================================

def get_thumbnail_url(public_id: str, fmt: str = None) -> str:
    """
    Thumbnail transformation: f_auto,q_auto,w_400,c_limit
    """
    if not public_id:
        return ""
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        format=fmt or None,
        transformation=[
            {'fetch_format': 'auto', 'quality': 'auto', 'width': 400, 'crop': 'limit'}
        ],
        secure=True
    )
    return url


def get_preview_url(public_id: str, fmt: str = None) -> str:
    """
    Gallery preview transformation: f_auto,q_auto,w_1200,c_limit
    """
    if not public_id:
        return ""
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        format=fmt or None,
        transformation=[
            {'fetch_format': 'auto', 'quality': 'auto', 'width': 1200, 'crop': 'limit'}
        ],
        secure=True
    )
    return url


def get_large_preview_url(public_id: str, fmt: str = None) -> str:
    """
    Large preview transformation: f_auto,q_auto,w_2000,c_limit
    """
    if not public_id:
        return ""
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        format=fmt or None,
        transformation=[
            {'fetch_format': 'auto', 'quality': 'auto', 'width': 2000, 'crop': 'limit'}
        ],
        secure=True
    )
    return url


def get_download_url(public_id: str, fmt: str = None, filename: str = None) -> str:
    """
    Original-quality download URL directly from Cloudinary CDN.
    Uses fl_attachment with the original filename to prompt browser download
    at full uncompressed resolution without routing bytes through Django.
    """
    if not public_id:
        return ""
    
    if filename:
        base_name, _ = os.path.splitext(filename)
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name or 'wedding_photo')
        attachment_flag = f"attachment:{clean_name}"
    else:
        attachment_flag = "attachment"

    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        format=fmt or None,
        flags=attachment_flag,
        secure=True
    )
    return url


def get_all_delivery_urls(public_id: str, fmt: str = None, filename: str = None) -> dict:
    """Returns a full mapping of CDN URLs for an asset."""
    original_url, _ = cloudinary.utils.cloudinary_url(public_id, format=fmt or None, secure=True)
    return {
        'secure_url': original_url,
        'thumbnail_url': get_thumbnail_url(public_id, fmt),
        'preview_url': get_preview_url(public_id, fmt),
        'large_preview_url': get_large_preview_url(public_id, fmt),
        'download_url': get_download_url(public_id, fmt, filename),
    }


# ==============================================================================
# Cloud-Saver Intelligent Image Compression (Fits 10,000 to 20,000 photos in Free Tier)
# ==============================================================================

def compress_image_to_target(
    file_path: str,
    min_mb: float = None,
    max_mb: float = None,
    max_kb: int = None,
    max_dim: int = None
) -> tuple:
    """
    Ensures an image uploaded to Cloudinary fits cleanly within the single Cloudinary
    Free Tier account storage budget (target 600-800 KB per photo, fitting 10,000 to 20,000 photos).
    - Preserves 2.5K Quad-HD (2560px) resolution for retina mobile screens and laptops.
    - If file is already <= max_bytes, returns (file_path, False) without recompression.
    - If file > max_bytes (e.g. 10-35 MB camera files), resizes to max_dimension and optimizes JPEG quality.
    - Returns (upload_path, is_temporary_file).
    """
    if max_kb is not None:
        max_bytes = int(max_kb * 1024)
    elif max_mb is not None:
        max_bytes = int(max_mb * 1024 * 1024)
    else:
        # Default from settings or environment: 750 KB (~0.73 MB)
        setting_kb = getattr(settings, 'CLOUDINARY_MAX_STORAGE_KB', None) or int(os.environ.get('CLOUDINARY_MAX_STORAGE_KB', '750'))
        max_bytes = int(setting_kb * 1024)

    target_dim = max_dim or getattr(settings, 'CLOUDINARY_MAX_DIMENSION', None) or int(os.environ.get('CLOUDINARY_MAX_DIMENSION', '2560'))

    size_bytes = os.path.getsize(file_path)
    if size_bytes <= max_bytes:
        return file_path, False

    logger.info(
        f"[Cloudinary] File {file_path} is {size_bytes / (1024*1024):.2f} MB (> {max_bytes / 1024:.0f} KB target). "
        f"Optimizing to fit 10k-20k photos Cloudinary free-tier budget..."
    )

    from PIL import Image, ImageOps
    import io
    import tempfile

    with Image.open(file_path) as im:
        # Pre-downscale in libjpeg DCT decoder for massive memory & CPU savings on large camera files
        try:
            im.draft('RGB', (target_dim, target_dim))
        except Exception:
            pass

        im = ImageOps.exif_transpose(im)
        if im.mode != 'RGB':
            im = im.convert('RGB')

        orig_w, orig_h = im.size
        max_dim_actual = max(orig_w, orig_h)
        
        # Maintain high resolution (up to 2560px Quad-HD is pin-sharp on retina screens)
        if max_dim_actual > target_dim:
            scale_ratio = target_dim / max_dim_actual
            im = im.resize((int(orig_w * scale_ratio), int(orig_h * scale_ratio)), Image.Resampling.BILINEAR)

        # Iterative quality selection to land within target byte budget
        best_data = None
        best_q = 84
        for q in [84, 80, 75, 70]:
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=q, optimize=True)
            data = buf.getvalue()
            cur_size = len(data)
            best_data = data
            best_q = q
            if cur_size <= max_bytes:
                break

        # If high-entropy photo is still above budget, scale to 2048px (2K)
        if len(best_data) > max_bytes and max(im.size) > 2048:
            scale_ratio = 2048 / max(im.size)
            im = im.resize((int(im.size[0] * scale_ratio), int(im.size[1] * scale_ratio)), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=75, optimize=True)
            best_data = buf.getvalue()

        # Write to temporary file for upload streaming
        fd, temp_path = tempfile.mkstemp(suffix="_cld_opt.jpg")
        os.close(fd)
        with open(temp_path, 'wb') as f:
            f.write(best_data)

        final_kb = len(best_data) / 1024
        logger.info(
            f"[Cloudinary] Successfully optimized {file_path} from {size_bytes / (1024*1024):.2f} MB "
            f"to {final_kb:.1f} KB (quality {best_q}, dim {im.size[0]}x{im.size[1]})"
        )
        return temp_path, True


# ==============================================================================
# Centralized Upload & Deletion Logic
# ==============================================================================

def upload_photo(file_path: str, wedding_slug: str, folder: str = 'Uncategorized',
                 checksum: str = None, original_filename: str = None,
                 max_retries: int = 3) -> dict:
    """
    Uploads a photograph to Cloudinary.
    - Compresses large DSLR photos (> 4 MB) down to the 3-4 MB target range.
    - Uses deterministic, predictable public ID.
    - Idempotent on retries: overwrite=True ensures duplicate assets are not created on network retries.
    - Validates response before returning.
    - Returns metadata: public_id, secure_url, format, width, height, bytes, resource_type, and CDN URLs.
    - When MOCK_CLOUDINARY is enabled (load-testing/staging), returns simulated Cloudinary CDN metadata
      without consuming production API quotas or external bandwidth.
    """
    if getattr(settings, 'MOCK_CLOUDINARY', False) or os.environ.get('MOCK_CLOUDINARY', '').lower() in ('1', 'true', 'yes'):
        mock_public_id = generate_public_id(wedding_slug, folder, checksum)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 3500000
        logger.info(f"[Mock Cloudinary] Simulated upload for {original_filename or file_path} -> '{mock_public_id}'")
        return {
            'public_id': mock_public_id,
            'secure_url': f"https://res.cloudinary.com/mock-cloud/image/upload/v1/{mock_public_id}.jpg",
            'cloudinary_url': f"http://res.cloudinary.com/mock-cloud/image/upload/v1/{mock_public_id}.jpg",
            'thumbnail_url': f"https://res.cloudinary.com/mock-cloud/image/upload/c_limit,f_auto,q_auto,w_400/v1/{mock_public_id}.jpg",
            'preview_url': f"https://res.cloudinary.com/mock-cloud/image/upload/c_limit,f_auto,q_auto,w_1200/v1/{mock_public_id}.jpg",
            'large_preview_url': f"https://res.cloudinary.com/mock-cloud/image/upload/c_limit,f_auto,q_auto,w_2000/v1/{mock_public_id}.jpg",
            'download_url': f"https://res.cloudinary.com/mock-cloud/image/upload/fl_attachment/v1/{mock_public_id}.jpg",
            'format': 'jpg',
            'width': 3000,
            'height': 2000,
            'bytes': file_size,
            'resource_type': 'image',
        }

    if not _is_configured and not configure_cloudinary():
        raise RuntimeError("Cloudinary is not properly configured. Check environment variables.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file for Cloudinary upload not found: {file_path}")

    # Target ~750 KB optimization before sending to Cloudinary (fits 10k-20k photos in free tier)
    upload_target, is_temp = compress_image_to_target(file_path)

    public_id = generate_public_id(wedding_slug, folder, checksum)
    last_error = None

    try:
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"[Cloudinary] Uploading {original_filename or file_path} -> public_id '{public_id}' "
                    f"(attempt {attempt + 1}/{max_retries}, upload size: {os.path.getsize(upload_target)/(1024*1024):.2f} MB)..."
                )

                result = cloudinary.uploader.upload(
                    upload_target,
                    public_id=public_id,
                    overwrite=True,             # Idempotent retry: overwrite exact public ID
                    invalidate=True,            # Invalidate CDN cache for modified assets
                    resource_type="image",
                    use_filename=False,
                    unique_filename=False,      # Enforce our exact hierarchical public_id
                    timeout=60                  # 60s socket timeout
                )

                # Verification of upload payload
                if not result.get('public_id') or not result.get('secure_url'):
                    raise ValueError(f"Incomplete Cloudinary upload response: {result}")

                res_bytes = result.get('bytes', 0)
                if res_bytes <= 0:
                    raise ValueError(f"Cloudinary reported 0 bytes uploaded for {file_path}")

                fmt = result.get('format', '')
                delivery_urls = get_all_delivery_urls(result['public_id'], fmt, original_filename)

                logger.info(
                    f"[Cloudinary] Upload successful: public_id={result['public_id']}, "
                    f"bytes={res_bytes}, dimensions={result.get('width')}x{result.get('height')}"
                )

                return {
                    'public_id': result['public_id'],
                    'secure_url': result['secure_url'],
                    'cloudinary_url': result.get('url', result['secure_url']),
                    'format': fmt,
                    'width': result.get('width'),
                    'height': result.get('height'),
                    'bytes': res_bytes,
                    'resource_type': result.get('resource_type', 'image'),
                    'created_at': result.get('created_at'),
                    'thumbnail_url': delivery_urls['thumbnail_url'],
                    'preview_url': delivery_urls['preview_url'],
                    'large_preview_url': delivery_urls['large_preview_url'],
                    'download_url': delivery_urls['download_url'],
                }

            except (socket.timeout, TimeoutError) as timeout_err:
                last_error = timeout_err
                logger.warning(f"[Cloudinary] Timeout on upload attempt {attempt + 1}: {timeout_err}")
            except cloudinary.exceptions.Error as cld_err:
                last_error = cld_err
                err_str = str(cld_err).lower()
                logger.warning(f"[Cloudinary] API Error on attempt {attempt + 1}: {cld_err}")
                # If hit rate limit or temporary server error, back off
                if 'rate limit' in err_str or 'try again' in err_str:
                    time.sleep(2 ** (attempt + 1))
                elif 'maximum is' in err_str or 'too large' in err_str:
                    # Fatal file limit error: do not retry
                    raise
            except Exception as exc:
                last_error = exc
                logger.warning(f"[Cloudinary] Unexpected exception on attempt {attempt + 1}: {exc}")

            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                time.sleep(backoff)

        raise last_error or RuntimeError(f"Cloudinary upload failed after {max_retries} attempts.")

    finally:
        # Clean up temporary compressed file while preserving original file on disk
        if is_temp and os.path.exists(upload_target):
            try:
                os.remove(upload_target)
            except OSError:
                pass


def delete_photo(public_id: str) -> bool:
    """
    Deletes an asset from Cloudinary and invalidates CDN edge caches.
    """
    if not public_id:
        return False
    if not _is_configured and not configure_cloudinary():
        return False

    try:
        logger.info(f"[Cloudinary] Destroying asset '{public_id}'...")
        res = cloudinary.uploader.destroy(public_id, invalidate=True)
        return res.get('result') in ['ok', 'not found']
    except Exception as e:
        logger.error(f"[Cloudinary] Failed to delete asset '{public_id}': {e}")
        return False


# ==============================================================================
# Usage & Plan Limit Monitoring
# ==============================================================================

def get_account_usage() -> dict:
    """
    Retrieves real-time account usage, plan limits, and credit consumption
    via Cloudinary Admin API.
    """
    if not _is_configured and not configure_cloudinary():
        raise RuntimeError("Cloudinary is not configured.")

    try:
        raw_usage = cloudinary.api.usage()
        credits_info = raw_usage.get('credits', {})
        storage_info = raw_usage.get('storage', {})
        bandwidth_info = raw_usage.get('bandwidth', {})
        trans_info = raw_usage.get('transformations', {})
        media_limits = raw_usage.get('media_limits', {})

        storage_bytes = storage_info.get('usage', 0)
        bandwidth_bytes = bandwidth_info.get('usage', 0)

        return {
            'plan': raw_usage.get('plan', 'Free'),
            'last_updated': raw_usage.get('last_updated'),
            'credits': {
                'usage': credits_info.get('usage', 0.0),
                'limit': credits_info.get('limit', 25.0),
                'used_percent': credits_info.get('used_percent', 0.0),
            },
            'storage': {
                'usage_bytes': storage_bytes,
                'usage_mb': round(storage_bytes / (1024 * 1024), 2),
                'usage_gb': round(storage_bytes / (1024 * 1024 * 1024), 3),
            },
            'bandwidth': {
                'usage_bytes': bandwidth_bytes,
                'usage_mb': round(bandwidth_bytes / (1024 * 1024), 2),
                'usage_gb': round(bandwidth_bytes / (1024 * 1024 * 1024), 3),
            },
            'transformations': {
                'usage': trans_info.get('usage', 0),
            },
            'media_limits': {
                'image_max_size_mb': round(media_limits.get('image_max_size_bytes', 10485760) / (1024 * 1024), 1),
                'image_max_pixels': media_limits.get('image_max_px', 25000000),
            },
            'resources_count': raw_usage.get('resources', 0),
        }
    except Exception as e:
        logger.error(f"[Cloudinary] Failed to retrieve account usage: {e}")
        return {
            'error': str(e),
            'plan': 'Unknown'
        }

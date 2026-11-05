import re
import io
import logging
from PIL import Image

logger = logging.getLogger('security')

# Magic bytes signature definitions
MAGIC_BYTES = {
    'jpeg': b'\xff\xd8\xff',
    'png': b'\x89PNG\r\n\x1a\n',
    'webp': b'RIFF',  # and bytes 8-12 == b'WEBP'
}

def get_client_ip(request) -> str:
    """Extracts client IP respecting proxy headers."""
    if not request:
        return 'unknown'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # First IP in comma-separated list is client IP
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')

def sanitize_audit_text(text: str) -> str:
    """Removes sensitive keys, passwords, and tokens from audit logs."""
    if not text:
        return ''
    # Mask potential passwords, tokens, auth headers, and 512-dim embedding floats
    masked = re.sub(r'(password|token|secret|api_key|key)=([^\s,&]+)', r'\1=[REDACTED]', str(text), flags=re.IGNORECASE)
    # Strip long numeric/vector arrays like [0.123, -0.456, ...]
    masked = re.sub(r'\[(\s*-?\d+\.\d+[\s,]*){5,}\]', '[BIOMETRIC_VECTOR_REDACTED]', masked)
    return masked[:500]

def audit_log(event: str, request=None, user=None, wedding_slug: str = None, details: str = None, level: str = 'info'):
    """
    Structured security audit logger.
    Logs authentication attempts, permission violations, file rejections, and deletions.
    Guarantees no cleartext credentials or biometric face vectors are logged.
    """
    ip = get_client_ip(request)
    username = 'anonymous'
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        username = getattr(user, 'username', str(user))
    elif request and hasattr(request, 'user') and request.user.is_authenticated:
        username = getattr(request.user, 'username', str(request.user))

    clean_details = sanitize_audit_text(details) if details else ''
    slug_str = f"wedding={wedding_slug}" if wedding_slug else "wedding=global"
    log_msg = f"[AUDIT] event={event} user={username} ip={ip} {slug_str} {clean_details}".strip()

    if level.lower() == 'warning':
        logger.warning(log_msg)
    elif level.lower() == 'error' or level.lower() == 'critical':
        logger.error(log_msg)
    else:
        logger.info(log_msg)

def validate_image_file_bytes(data: bytes, max_size: int = 10 * 1024 * 1024, min_size: int = 1024) -> str:
    """
    Validates uploaded image data in-memory:
    1. Size bounds check (min 1KB, max 10MB default)
    2. Magic bytes verification (JPEG, PNG, WEBP)
    3. Structural image verification via PIL verify()
    Returns normalized format name ('jpeg', 'png', 'webp') or raises ValueError.
    """
    total_bytes = len(data)
    if total_bytes < min_size:
        raise ValueError(f"File is too small ({total_bytes} bytes). Incomplete or corrupted image.")

    if total_bytes > max_size:
        max_mb = max_size // (1024 * 1024)
        raise ValueError(f"File size exceeds maximum limit of {max_mb} MB.")

    # 1. Magic bytes check
    detected_format = None
    if data.startswith(MAGIC_BYTES['jpeg']):
        detected_format = 'jpeg'
    elif data.startswith(MAGIC_BYTES['png']):
        detected_format = 'png'
    elif data.startswith(MAGIC_BYTES['webp']) and len(data) >= 12 and data[8:12] == b'WEBP':
        detected_format = 'webp'
    else:
        raise ValueError("Invalid file signature. File does not match supported image types (JPEG, PNG, WEBP).")

    # 2. PIL verify() check to protect against decompressed bombs / malformed chunk headers
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
            fmt = (img.format or '').lower()
            if fmt not in ['jpeg', 'png', 'webp', 'mpo']:
                raise ValueError(f"Unrecognized or unsupported image container format: {fmt}")
            if fmt == 'mpo':
                detected_format = 'jpeg'
    except Exception as exc:
        raise ValueError(f"Malformed or corrupted image content: {exc}")

    return detected_format


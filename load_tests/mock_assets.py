"""
Generates in-memory mock test assets for load testing:
- Valid JPEG images with correct magic bytes (\xff\xd8\xff)
- Varying dimensions and byte sizes to simulate real mobile selfies and photographer uploads.
"""

import io
from PIL import Image, ImageDraw


def generate_mock_jpeg(width: int = 640, height: int = 640, text: str = "Test Image") -> bytes:
    """Generates a valid JPEG image buffer with drawing and valid headers."""
    img = Image.new("RGB", (width, height), color=(180, 200, 220))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], outline=(40, 60, 100), width=4)
    draw.ellipse([width // 4, height // 4, 3 * width // 4, 3 * height // 4], fill=(220, 160, 140))
    # Simple simulated eyes/smile so face detection can identify or gracefully reject
    draw.ellipse([width // 3 - 10, height // 3, width // 3 + 10, height // 3 + 20], fill=(0, 0, 0))
    draw.ellipse([2 * width // 3 - 10, height // 3, 2 * width // 3 + 10, height // 3 + 20], fill=(0, 0, 0))
    draw.arc([width // 3, height // 2, 2 * width // 3, 2 * height // 3], start=0, end=180, fill=(0, 0, 0), width=4)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


MOCK_SELFIE_JPEG = generate_mock_jpeg(480, 640, "Selfie")
MOCK_PHOTO_JPEG = generate_mock_jpeg(1200, 800, "Camera Photo")


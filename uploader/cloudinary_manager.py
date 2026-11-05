import os
import re
import tempfile
import io
from datetime import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from dotenv import load_dotenv
from PIL import Image, ImageOps

# Load environment variables from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def compress_to_cloud_saver(file_path: str, max_kb: int = 750, max_dim: int = 2560) -> tuple:
    """
    Mandatory Cloud-Saver optimization: ensures EVERY photo uploaded to Cloudinary
    is compressed to ~500-750 KB at 2.5K Quad-HD (2560px max dimension).
    Fits 20,000+ photos in Cloudinary Free Tier. Completely removes raw uncompressed uploads.
    """
    size_bytes = os.path.getsize(file_path)
    max_bytes = max_kb * 1024

    if size_bytes <= max_bytes:
        return file_path, False

    with Image.open(file_path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode != 'RGB':
            im = im.convert('RGB')

        orig_w, orig_h = im.size
        max_dim_actual = max(orig_w, orig_h)
        if max_dim_actual > max_dim:
            ratio = max_dim / max_dim_actual
            im = im.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.LANCZOS)

        best_data = None
        for q in [86, 82, 78, 74, 70]:
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=q, optimize=True, progressive=True)
            data = buf.getvalue()
            best_data = data
            if len(data) <= max_bytes:
                break

        if len(best_data) > max_bytes and max(im.size) > 2048:
            ratio = 2048 / max(im.size)
            im = im.resize((int(im.size[0] * ratio), int(im.size[1] * ratio)), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=80, optimize=True, progressive=True)
            best_data = buf.getvalue()

        fd, temp_path = tempfile.mkstemp(suffix="_cld_opt.jpg")
        os.close(fd)
        with open(temp_path, 'wb') as f:
            f.write(best_data)

        print(f"Cloud-Saver: {os.path.basename(file_path)}: {size_bytes/(1024*1024):.1f}MB -> {len(best_data)/1024:.1f}KB (target <={max_kb}KB)")
        return temp_path, True

# Alias for backwards compatibility
compress_to_target_3_4mb = compress_to_cloud_saver

class CloudinaryManager:
    """
    Centralized Cloudinary Manager for Uploader CLI.
    Strictly uses a single Cloudinary account defined by:
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET.
    Compresses large DSLR photos to 3-4 MB target range.
    """
    def __init__(self):
        self.cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
        self.api_key = os.environ.get('CLOUDINARY_API_KEY')
        self.api_secret = os.environ.get('CLOUDINARY_API_SECRET')
        self.wedding_slug = os.environ.get('WEDDING_SLUG', 'sandeep-prathyusha')

        if not all([self.cloud_name, self.api_key, self.api_secret]):
            print("ERROR: Missing Cloudinary credentials! Ensure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET are set.")
        else:
            cloudinary.config(
                cloud_name=self.cloud_name.strip(),
                api_key=self.api_key.strip(),
                api_secret=self.api_secret.strip(),
                secure=True
            )

    def generate_public_id(self, checksum: str, filename: str) -> str:
        date_str = datetime.now().strftime('%Y-%m-%d')
        short_hash = (checksum or 'photo')[:16]
        return f"weddings/{self.wedding_slug}/originals/{date_str}/{short_hash}"

    def upload_image(self, file_path: str, checksum: str = None) -> dict:
        """
        Uploads a photograph to Cloudinary, ensuring file is optimized to 3-4 MB.
        Idempotent: uses deterministic public ID and overwrite=True.
        """
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist.")
            return None

        filename = os.path.basename(file_path)
        public_id = self.generate_public_id(checksum, filename)

        upload_target, is_temp = compress_to_target_3_4mb(file_path)

        try:
            print(f"Uploading {filename} to Cloudinary ({os.path.getsize(upload_target)/(1024*1024):.2f} MB) -> public_id: {public_id}...")
            response = cloudinary.uploader.upload(
                upload_target,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                use_filename=False,
                unique_filename=False,
                timeout=60
            )

            # Build dynamic thumbnail URL (w_400,c_limit,f_auto,q_auto) directly via CDN
            thumbnail_url, _ = cloudinary.utils.cloudinary_url(
                response['public_id'],
                format=response.get('format'),
                transformation=[
                    {'fetch_format': 'auto', 'quality': 'auto', 'width': 400, 'crop': 'limit'}
                ],
                secure=True
            )

            preview_url, _ = cloudinary.utils.cloudinary_url(
                response['public_id'],
                format=response.get('format'),
                transformation=[
                    {'fetch_format': 'auto', 'quality': 'auto', 'width': 1200, 'crop': 'limit'}
                ],
                secure=True
            )

            return {
                'public_id': response.get('public_id'),
                'secure_url': response.get('secure_url'),
                'thumbnail_url': thumbnail_url,
                'preview_url': preview_url,
                'width': response.get('width'),
                'height': response.get('height'),
                'bytes': response.get('bytes'),
                'format': response.get('format'),
                'resource_type': response.get('resource_type', 'image')
            }

        except Exception as e:
            print(f"Cloudinary upload failed for {filename}: {e}")
            return None
        finally:
            if is_temp and os.path.exists(upload_target):
                try:
                    os.remove(upload_target)
                except OSError:
                    pass

# Singleton instance
cloudinary_manager = CloudinaryManager()

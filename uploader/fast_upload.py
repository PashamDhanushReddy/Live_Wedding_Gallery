"""
Fast batch uploader - skips face detection, uses 4 parallel threads.
Uploads compress + upload + sync simultaneously for maximum speed.
"""
import os
import sys
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_1_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_1_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_1_API_SECRET')
)

API_URL = os.environ.get('API_URL', 'http://127.0.0.1:8000/api')
WEDDING_SLUG = os.environ.get('WEDDING_SLUG', 'sandeep-prathyusha')
FOLDER = os.path.join(os.path.dirname(__file__), 'WATCH_FOLDER')
MAX_WORKERS = 4  # Upload 4 photos at the same time

def calculate_checksum(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def compress_image(file_path):
    """Compress image to target ~1-2 MB size while preserving clarity."""
    with Image.open(file_path) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        max_dim = 2560
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(tmp.name, format='JPEG', quality=85, optimize=True)
        return tmp.name

def upload_one(file_path):
    filename = os.path.basename(file_path)
    try:
        checksum = calculate_checksum(file_path)

        # Check DB directly to see if this checksum is already in photos_photo
        import psycopg2
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            try:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM photos_photo WHERE checksum = %s", (checksum,))
                if cursor.fetchone():
                    print(f"[SKIP] [{filename}] Already uploaded.")
                    conn.close()
                    return True
                conn.close()
            except Exception as e:
                pass # Fallback to normal upload if DB check fails

        # Compress if over 2MB
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 2:
            tmp_path = compress_image(file_path)
            print(f"[{filename}] Compressed {size_mb:.1f}MB -> {os.path.getsize(tmp_path)/(1024*1024):.2f}MB")
        else:
            tmp_path = file_path

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            tmp_path,
            folder='live_wedding_album',
            resource_type='image'
        )

        if tmp_path != file_path:
            os.unlink(tmp_path)

        secure_url = result['secure_url']
        # Generate thumbnail URL via Cloudinary transformation
        thumb_url = secure_url.replace('/upload/', '/upload/c_thumb,w_400,h_400/')

        # Sync to Django
        # checksum was already calculated at the top of the function
        photo_data = {
            "original_filename": filename,
            "cloudinary_public_id": result['public_id'],
            "cloudinary_url": secure_url,
            "secure_url": secure_url,
            "thumbnail_url": thumb_url,
            "width": result.get('width', 0),
            "height": result.get('height', 0),
            "file_size": result.get('bytes', 0),
            "checksum": checksum,
            "faces": []
        }
        resp = requests.post(
            f"{API_URL}/weddings/{WEDDING_SLUG}/sync/",
            json=photo_data,
            timeout=15
        )
        if resp.status_code in (200, 201):
            print(f"[OK] [{filename}] Done -> {secure_url}")
            return True
        else:
            print(f"[WARN] [{filename}] Uploaded but sync failed: {resp.status_code}")
            return False

    except Exception as e:
        print(f"[FAIL] [{filename}] Error: {e}")
        return False

def main():
    files = sorted([
        os.path.join(FOLDER, f) for f in os.listdir(FOLDER)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic'))
    ])
    
    print(f"Found {len(files)} photos. Uploading with {MAX_WORKERS} parallel workers...")
    print("")
    
    success = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(upload_one, f): f for f in files}
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1

    print("=" * 40)
    print(f"[DONE] Success: {success} | Failed: {failed} | Total: {len(files)}")

if __name__ == '__main__':
    main()

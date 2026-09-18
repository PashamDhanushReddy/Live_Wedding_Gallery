import os
import time
import hashlib
from queue_manager import update_checksum, update_status

FILE_STABLE_CHECK_INTERVAL = int(os.environ.get('FILE_STABLE_CHECK_INTERVAL', 1))
FILE_STABLE_CHECK_COUNT = int(os.environ.get('FILE_STABLE_CHECK_COUNT', 2))

def calculate_checksum(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating checksum for {file_path}: {e}")
        return None

def wait_for_file_stability(file_path):
    print(f"Checking stability for {file_path}...")
    stable_count = 0
    previous_size = -1

    while stable_count < FILE_STABLE_CHECK_COUNT:
        if not os.path.exists(file_path):
            print(f"File {file_path} disappeared during stability check.")
            return False
            
        current_size = os.path.getsize(file_path)
        if current_size == previous_size:
            stable_count += 1
        else:
            stable_count = 0
            previous_size = current_size
            
        time.sleep(FILE_STABLE_CHECK_INTERVAL)
        
    print(f"File {file_path} is stable. Size: {previous_size} bytes.")
    return True

def process_file(file_path):
    if not wait_for_file_stability(file_path):
        update_status(file_path, 'FAILED')
        return

    checksum = calculate_checksum(file_path)
    if not checksum:
        update_status(file_path, 'FAILED')
        return

    # Update the DB. If IntegrityError is caught (False returned), it's a duplicate.
    if not update_checksum(file_path, checksum):
        print(f"Duplicate detected: {file_path} (Checksum: {checksum})")
        update_status(file_path, 'DUPLICATE')
        return
        
    print(f"File {file_path} is unique. Ready for upload.")
    update_status(file_path, 'PROCESSING')
    
    # Check for faces locally before uploading
    from face_analyzer import analyze_faces
    from queue_manager import update_faces_data, update_cloudinary_metadata
    import json
    
    print(f"Analyzing faces for {file_path}...")
    faces = analyze_faces(file_path)
    if faces:
        update_faces_data(file_path, json.dumps(faces))
    
    # Upload to Cloudinary
    from cloudinary_manager import cloudinary_manager
    from api_client import sync_photo_to_server
    import os
    
    # Compress image if over 2MB for faster uploads
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 2:
        try:
            from PIL import Image
            import tempfile
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                max_dim = 2560
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                tmp.close() # Close the file descriptor so Windows allows PIL and os to access/delete it
                img.save(tmp.name, format='JPEG', quality=85, optimize=True)
                upload_target = tmp.name
                print(f"Compressed {size_mb:.1f}MB -> {os.path.getsize(upload_target)/(1024*1024):.2f}MB")
        except Exception as e:
            print(f"Compression failed: {e}")
            upload_target = file_path
    else:
        upload_target = file_path

    upload_result = cloudinary_manager.upload_image(upload_target)
    
    if upload_target != file_path:
        try:
            os.unlink(upload_target)
        except Exception as e:
            print(f"Failed to delete temp file {upload_target}: {e}")

    if upload_result:
        update_cloudinary_metadata(
            file_path,
            upload_result['public_id'],
            upload_result['secure_url'],
            upload_result['thumbnail_url']
        )
        print(f"Upload successful: {upload_result['secure_url']}")

        # Prepare data for Django API
        photo_data = {
            "original_filename": os.path.basename(file_path),
            "cloudinary_public_id": upload_result['public_id'],
            "cloudinary_url": upload_result['secure_url'],
            "secure_url": upload_result['secure_url'],
            "thumbnail_url": upload_result['thumbnail_url'],
            "width": upload_result['width'],
            "height": upload_result['height'],
            "file_size": upload_result['bytes'],
            "checksum": calculate_checksum(file_path),
            "faces": faces if faces else []
        }

        success, response = sync_photo_to_server(photo_data)
        if success:
            print("Successfully synced to Django server!")
            update_status(file_path, 'COMPLETED')
        else:
            print("Failed to sync to Django server. Marked as PENDING_SYNC.")
            update_status(file_path, 'PENDING_SYNC')

    else:
        print(f"Upload failed for {file_path}")
        update_status(file_path, 'FAILED')

def retry_sync_file(file_path):
    from queue_manager import get_upload_metadata, update_status
    from api_client import sync_photo_to_server
    import os
    import json
    
    print(f"Retrying sync for {file_path}...")
    metadata = get_upload_metadata(file_path)
    if not metadata or not metadata.get('public_id'):
        print(f"Cannot retry sync for {file_path} - missing metadata.")
        update_status(file_path, 'FAILED')
        return

    faces = []
    if metadata.get('faces_data'):
        try:
            faces = json.loads(metadata['faces_data'])
        except Exception:
            pass

    width, height = 0, 0
    file_size = 0
    if os.path.exists(file_path):
        try:
            file_size = os.path.getsize(file_path)
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            print(f"Error getting image dimensions for {file_path}: {e}")

    photo_data = {
        "original_filename": os.path.basename(file_path),
        "cloudinary_public_id": metadata['public_id'],
        "cloudinary_url": metadata['secure_url'],
        "secure_url": metadata['secure_url'],
        "thumbnail_url": metadata['thumbnail_url'],
        "width": width,
        "height": height,
        "file_size": file_size,
        "checksum": metadata['checksum'],
        "faces": faces
    }

    success, response = sync_photo_to_server(photo_data)
    if success:
        print(f"Successfully synced {file_path} to Django server on retry!")
        update_status(file_path, 'COMPLETED')
    else:
        print(f"Retry sync failed for {file_path}. Will try again later.")

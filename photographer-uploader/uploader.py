import os
import time
import hashlib
import shutil
import requests
from database import init_db, add_to_queue, get_pending_uploads, update_status

# Configuration
WEDDING_SLUG = os.environ.get("WEDDING_SLUG", "test-wedding")
API_URL = os.environ.get("API_URL", f"http://localhost:8000/api/weddings/{WEDDING_SLUG}/photos/upload/")
IMPORT_DIR = 'import'
UPLOADED_DIR = 'uploaded'
FAILED_DIR = 'failed'
DB_PATH = 'queue.db'
POLL_INTERVAL = 2

def setup_directories():
    for d in [IMPORT_DIR, UPLOADED_DIR, FAILED_DIR]:
        os.makedirs(d, exist_ok=True)

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_import_directory():
    for filename in os.listdir(IMPORT_DIR):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic')):
            continue
            
        filepath = os.path.join(IMPORT_DIR, filename)
        
        # Wait a moment to ensure file is completely written (simple heuristic)
        time.sleep(0.5) 
        
        try:
            sha256 = calculate_sha256(filepath)
            if add_to_queue(filepath, sha256, DB_PATH):
                print(f"Added to queue: {filename}")
            else:
                print(f"Skipped duplicate: {filename}")
                # Move to uploaded since it's a duplicate in queue
                shutil.move(filepath, os.path.join(UPLOADED_DIR, filename))
        except Exception as e:
            print(f"Error scanning {filename}: {e}")

def process_queue():
    pending = get_pending_uploads(DB_PATH)
    
    for item in pending:
        photo_id = item['id']
        filepath = item['path']
        filename = os.path.basename(filepath)
        retry_count = item['retry_count']
        
        # Exponential backoff (max 5 minutes)
        if item['status'] == 'FAILED' and retry_count > 0:
            backoff = min(5 * (2 ** (retry_count - 1)), 300)
            print(f"Backing off for {backoff} seconds for {filename}...")
            time.sleep(backoff)
            
        if not os.path.exists(filepath):
            print(f"File missing: {filepath}")
            update_status(photo_id, 'MISSING', "File not found on disk", DB_PATH)
            continue
            
        print(f"Uploading {filename}...")
        
        try:
            with open(filepath, 'rb') as f:
                files = {'photo': (filename, f, 'image/jpeg')} # Assume jpeg for now
                response = requests.post(API_URL, files=files, timeout=30)
                
            if response.status_code in [200, 201]:
                print(f"Upload successful: {filename}")
                update_status(photo_id, 'UPLOADED', db_path=DB_PATH)
                # Move to uploaded dir
                try:
                    shutil.move(filepath, os.path.join(UPLOADED_DIR, filename))
                except Exception:
                    pass
            else:
                print(f"Upload failed: {response.status_code} - {response.text}")
                update_status(photo_id, 'FAILED', f"HTTP {response.status_code}: {response.text}", DB_PATH)
                
        except requests.exceptions.RequestException as e:
            print(f"Network error during upload: {e}")
            update_status(photo_id, 'FAILED', str(e), DB_PATH)
            # Break to avoid hammering the network if it's down
            break

def main():
    print("Starting Photographer Uploader...")
    init_db(DB_PATH)
    setup_directories()
    
    print(f"Watching {IMPORT_DIR} directory...")
    
    try:
        while True:
            scan_import_directory()
            process_queue()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nUploader stopped.")

if __name__ == "__main__":
    main()

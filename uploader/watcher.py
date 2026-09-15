import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Initialize a global thread pool to limit concurrent connections and memory usage
executor = ThreadPoolExecutor(max_workers=3)

from queue_manager import add_file, batch_add_files, get_pending_uploads, reset_stuck_uploads, get_pending_sync_uploads
from processor import process_file, retry_sync_file

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

WATCH_FOLDER = os.environ.get('WATCH_FOLDER', os.path.join(os.path.dirname(__file__), 'WATCH_FOLDER'))
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}

class PhotoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_ext = os.path.splitext(event.src_path)[1].lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            return
            
        print(f"New image detected: {event.src_path}")
        
        # Add to local sqlite queue
        if add_file(event.src_path):
            # Queue to executor
            executor.submit(process_file, event.src_path)
        else:
            print(f"File already in queue: {event.src_path}")

import socket

def start_watching():
    # Ensure only a single instance of watcher is running
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _lock_socket.bind(('127.0.0.1', 49152))
    except socket.error:
        print("Watcher is already running. Exiting.")
        return

    if not os.path.exists(WATCH_FOLDER):
        print(f"Creating watch folder: {WATCH_FOLDER}")
        os.makedirs(WATCH_FOLDER, exist_ok=True)
        
    event_handler = PhotoHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    
    print(f"Starting watcher on folder: {WATCH_FOLDER}")
    observer.start()
    
    # Scan directory for existing files that might not be in DB
    print("Scanning directory for unindexed files...")
    # Get all existing files in one query to avoid remote DB latency
    import psycopg2
    try:
        from queue_manager import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM queue_uploads")
        existing_files = set(row[0] for row in cursor.fetchall())
        conn.close()
    except Exception as e:
        print(f"Error fetching existing files: {e}")
        existing_files = set()

    missing_files = []
    for filename in os.listdir(WATCH_FOLDER):
        file_path = os.path.join(WATCH_FOLDER, filename)
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in SUPPORTED_EXTENSIONS:
                if file_path not in existing_files:
                    missing_files.append(file_path)
    
    if missing_files:
        print(f"Adding {len(missing_files)} missing files to the database...")
        batch_add_files(missing_files)

    # Process any pending files from previous runs
    reset_stuck_uploads()
    pending = get_pending_uploads()
    if pending:
        print(f"Found {len(pending)} pending files. Resuming processing...")
        for p_file in pending:
            if os.path.exists(p_file):
                executor.submit(process_file, p_file)
            
    try:
        last_sync_retry = time.time()
        while True:
            time.sleep(1)
            # Retry offline syncs and scan for missing files every 30 seconds
            if time.time() - last_sync_retry > 30:
                last_sync_retry = time.time()
                
                # 1. Scan directory for any missed files
                for filename in os.listdir(WATCH_FOLDER):
                    file_path = os.path.join(WATCH_FOLDER, filename)
                    if os.path.isfile(file_path):
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in SUPPORTED_EXTENSIONS:
                            if add_file(file_path):
                                print(f"Found missing file during periodic scan: {file_path}")
                                executor.submit(process_file, file_path)

                # 2. Retry offline syncs
                pending_syncs = get_pending_sync_uploads()
                if pending_syncs:
                    print(f"Found {len(pending_syncs)} files pending offline sync. Retrying...")
                    for p_file in pending_syncs:
                        if os.path.exists(p_file):
                            executor.submit(retry_sync_file, p_file)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()

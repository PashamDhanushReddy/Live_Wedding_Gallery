import os
import sqlite3
from uploader.queue_manager import add_file, QUEUE_DB

def resync_queue():
    folder = 'uploader/WATCH_FOLDER'
    conn = sqlite3.connect(QUEUE_DB, timeout=30)
    cursor = conn.cursor()
    
    # 1. Reset FAILED and PROCESSING to PENDING
    cursor.execute("UPDATE uploads SET status = 'PENDING' WHERE status IN ('FAILED', 'PROCESSING')")
    print(f"Reset {cursor.rowcount} FAILED/PROCESSING items to PENDING")
    conn.commit()
    
    # 2. Add missing files from WATCH_FOLDER
    added = 0
    for filename in os.listdir(folder):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic')):
            continue
            
        file_path = os.path.join(folder, filename)
        # Check if exists in DB
        cursor.execute("SELECT 1 FROM uploads WHERE file_path = ?", (file_path,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO uploads (file_path, status) VALUES (?, 'PENDING')", (file_path,))
            added += 1
            
    conn.commit()
    conn.close()
    print(f"Added {added} missing files to queue")

if __name__ == '__main__':
    resync_queue()

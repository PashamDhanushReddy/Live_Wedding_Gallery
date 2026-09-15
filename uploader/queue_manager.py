import psycopg2
import os
import threading
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.environ.get('DATABASE_URL')
db_lock = threading.Lock()

def get_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue_uploads (
                id SERIAL PRIMARY KEY,
                file_path TEXT UNIQUE,
                checksum TEXT UNIQUE,
                status TEXT DEFAULT 'PENDING',
                cloudinary_public_id TEXT,
                cloudinary_secure_url TEXT,
                cloudinary_thumbnail_url TEXT,
                faces_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

def add_file(file_path):
    with db_lock:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO queue_uploads (file_path) VALUES (%s)",
                (file_path,)
            )
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            if conn:
                conn.rollback()
            return False  # Already exists
        except Exception as e:
            print(f"Error adding file {file_path}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

def batch_add_files(file_paths):
    if not file_paths:
        return []
    import psycopg2.extras
    with db_lock:
        conn = None
        added = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Use execute_values for true batch insert
            # ON CONFLICT DO NOTHING ensures we don't crash on duplicates
            query = "INSERT INTO queue_uploads (file_path) VALUES %s ON CONFLICT (file_path) DO NOTHING"
            
            psycopg2.extras.execute_values(
                cursor,
                query,
                [(fp,) for fp in file_paths]
            )
            conn.commit()
            return file_paths
        except Exception as e:
            print(f"Error in batch_add_files: {e}")
            if conn:
                conn.rollback()
            return []
        finally:
            if conn:
                conn.close()

def update_checksum(file_path, checksum):
    with db_lock:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE queue_uploads SET checksum = %s, updated_at = %s WHERE file_path = %s",
                (checksum, datetime.now(), file_path)
            )
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            if conn:
                conn.rollback()
            return False  # Duplicate checksum
        except Exception as e:
            print(f"Error updating checksum for {file_path}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

def update_status(file_path, status):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE queue_uploads SET status = %s, updated_at = %s WHERE file_path = %s",
            (status, datetime.now(), file_path)
        )
        conn.commit()
        conn.close()

def update_faces_data(file_path, faces_json):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE queue_uploads SET faces_data = %s, updated_at = %s WHERE file_path = %s",
            (faces_json, datetime.now(), file_path)
        )
        conn.commit()
        conn.close()

def update_cloudinary_metadata(file_path, public_id, secure_url, thumbnail_url):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE queue_uploads 
               SET cloudinary_public_id = %s, 
                   cloudinary_secure_url = %s, 
                   cloudinary_thumbnail_url = %s,
                   updated_at = %s 
               WHERE file_path = %s""",
            (public_id, secure_url, thumbnail_url, datetime.now(), file_path)
        )
        conn.commit()
        conn.close()

def reset_stuck_uploads():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE queue_uploads SET status = 'PENDING' WHERE status IN ('PROCESSING', 'FAILED')")
        conn.commit()
        conn.close()

def get_pending_uploads():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM queue_uploads WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

def get_pending_sync_uploads():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM queue_uploads WHERE status = 'PENDING_SYNC'")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

def get_upload_metadata(file_path):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cloudinary_public_id, cloudinary_secure_url, cloudinary_thumbnail_url, faces_data, checksum
               FROM queue_uploads WHERE file_path = %s""",
            (file_path,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "public_id": row[0],
                "secure_url": row[1],
                "thumbnail_url": row[2],
                "faces_data": row[3],
                "checksum": row[4]
            }
        return None

# Initialize db on import
init_db()

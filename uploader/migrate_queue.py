import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.environ.get('DATABASE_URL')

def migrate():
    print("Connecting to Neon DB...")
    pg_conn = psycopg2.connect(DB_URL)
    pg_cursor = pg_conn.cursor()

    # Create the table if it doesn't exist
    print("Creating queue_uploads table in PostgreSQL...")
    pg_cursor.execute('''
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
    pg_conn.commit()

    print("Connecting to local SQLite DB...")
    sqlite_conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'queue.db'))
    sqlite_cursor = sqlite_conn.cursor()

    print("Reading data from SQLite...")
    sqlite_cursor.execute("SELECT id, file_path, checksum, status, cloudinary_public_id, cloudinary_secure_url, cloudinary_thumbnail_url, faces_data, created_at, updated_at FROM uploads")
    rows = sqlite_cursor.fetchall()

    print(f"Migrating {len(rows)} records...")
    for row in rows:
        try:
            pg_cursor.execute('''
                INSERT INTO queue_uploads (id, file_path, checksum, status, cloudinary_public_id, cloudinary_secure_url, cloudinary_thumbnail_url, faces_data, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', row)
        except psycopg2.IntegrityError:
            pg_conn.rollback()
            continue
        except Exception as e:
            print(f"Error migrating row {row[0]}: {e}")
            pg_conn.rollback()
        else:
            pg_conn.commit()

    # Update sequence for auto-increment ID in Postgres
    if rows:
        pg_cursor.execute("SELECT setval(pg_get_serial_sequence('queue_uploads', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM queue_uploads;")
        pg_conn.commit()

    print("Migration complete!")
    pg_conn.close()
    sqlite_conn.close()

if __name__ == '__main__':
    migrate()

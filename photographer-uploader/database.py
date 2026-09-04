import sqlite3
import os

def get_connection(db_path='queue.db'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path='queue.db'):
    conn = get_connection(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS photo_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_to_queue(path, sha256, db_path='queue.db'):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM photo_queue WHERE sha256 = ?', (sha256,))
    if cursor.fetchone():
        conn.close()
        return False
    
    cursor.execute('''
        INSERT INTO photo_queue (path, sha256, status)
        VALUES (?, ?, 'PENDING')
    ''', (path, sha256))
    conn.commit()
    conn.close()
    return True

def get_pending_uploads(db_path='queue.db'):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM photo_queue 
        WHERE status = 'PENDING' OR status = 'FAILED'
        ORDER BY created_at ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_status(photo_id, status, error=None, db_path='queue.db'):
    conn = get_connection(db_path)
    if status == 'FAILED':
        conn.execute('''
            UPDATE photo_queue 
            SET status = ?, last_error = ?, retry_count = retry_count + 1
            WHERE id = ?
        ''', (status, str(error), photo_id))
    else:
        conn.execute('''
            UPDATE photo_queue 
            SET status = ?
            WHERE id = ?
        ''', (status, photo_id))
    conn.commit()
    conn.close()

import sqlite3
import os

conn = sqlite3.connect('uploader/queue.db')
cursor = conn.cursor()
cursor.execute("SELECT id, file_path FROM uploads WHERE status='PENDING'")
rows = cursor.fetchall()
for row in rows:
    id, file_path = row
    if file_path.startswith('WATCH_FOLDER'):
        new_path = os.path.join('uploader', file_path)
        cursor.execute("UPDATE uploads SET file_path = ? WHERE id = ?", (new_path, id))
conn.commit()
conn.close()
print("Paths fixed!")

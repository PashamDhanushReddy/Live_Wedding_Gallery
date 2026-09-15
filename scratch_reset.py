import sqlite3
conn = sqlite3.connect('uploader/queue.db')
cursor = conn.cursor()
cursor.execute("UPDATE uploads SET status = 'PENDING' WHERE status IN ('FAILED', 'PROCESSING')")
print(f'Reset {cursor.rowcount} items')
conn.commit()
conn.close()

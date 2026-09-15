import os, django, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
c = connection.cursor()

# Get all tables in public schema
c.execute("""
    SELECT tablename FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY tablename
""")
tables = [r[0] for r in c.fetchall()]
print("All tables:", tables)

# Drop all of them
for t in tables:
    try:
        c.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')
        print(f"Dropped {t}")
    except Exception as e:
        print(f"Could not drop {t}: {e}")

connection.connection.commit()
print("\nAll tables dropped. Now run migrations.")

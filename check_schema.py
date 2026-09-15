import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Load env
from dotenv import load_dotenv
load_dotenv()

django.setup()

from django.db import connection
c = connection.cursor()
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='weddings_wedding' ORDER BY ordinal_position")
cols = [r[0] for r in c.fetchall()]
print("Columns:", cols)

# Add missing columns if needed
missing = []
needed = ['bride_name', 'groom_name', 'wedding_title', 'venue', 'description', 'cover_image', 'is_active']
for col in needed:
    if col not in cols:
        missing.append(col)
print("Missing columns:", missing)

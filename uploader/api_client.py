import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_URL = os.environ.get('API_URL', 'http://127.0.0.1:8000/api')
WEDDING_SLUG = os.environ.get('WEDDING_SLUG', 'rahul-weds-priya')
API_KEY = os.environ.get('API_KEY', 'development_key')

def sync_photo_to_server(photo_data):
    """
    Sends photo metadata and face embeddings to the Django server.
    """
    endpoint = f"{API_URL}/weddings/{WEDDING_SLUG}/sync/"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(endpoint, json=photo_data, headers=headers, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to sync photo to server: {e}")
        return False, str(e)

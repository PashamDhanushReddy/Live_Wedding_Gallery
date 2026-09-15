import requests
r = requests.get('http://127.0.0.1:8000/api/weddings/sandeep-prathyusha/photos/')
photos = r.json()
print(f"Total: {len(photos)}")
print(f"Unique URLs: {len(set(p.get('secure_url') for p in photos))}")
print(f"Unique IDs: {len(set(p.get('id') for p in photos))}")

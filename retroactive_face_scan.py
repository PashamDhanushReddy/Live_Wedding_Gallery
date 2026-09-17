import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from photos.models import Photo
from faces.models import Face
from uploader.face_analyzer import analyze_faces

FOLDER = os.path.join(os.path.dirname(__file__), 'uploader', 'WATCH_FOLDER')

def run():
    print("Starting retroactive face scan...")
    photos = Photo.objects.all()
    count = 0
    total_faces = 0

    for photo in photos:
        # Check if faces already exist
        if Face.objects.filter(photo=photo).exists():
            from photos.categorization import categorize_photo
            categorize_photo(photo)
            continue

        file_path = os.path.join(FOLDER, photo.original_filename)
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        print(f"[{count+1}/{photos.count()}] Analyzing {photo.original_filename}...")
        faces_data = analyze_faces(file_path)
        
        if faces_data:
            for face_data in faces_data:
                bbox = face_data.get('bbox', [0, 0, 0, 0])
                Face.objects.create(
                    photo=photo,
                    embedding=face_data.get('embedding'),
                    x=bbox[0],
                    y=bbox[1],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                    detection_confidence=face_data.get('confidence', 1.0)
                )
            total_faces += len(faces_data)
            print(f"  -> Added {len(faces_data)} faces.")
            
            from photos.categorization import categorize_photo
            categorize_photo(photo)
        else:
            print("  -> No faces found.")
        
        count += 1

    print(f"Done! Scanned {count} photos and extracted {total_faces} faces.")

if __name__ == "__main__":
    run()

import os
import sys
import django
import urllib.request
import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from photos.models import Photo
from faces.models import Face
from photos.categorization import categorize_photo

def main():
    print("=======================================")
    print("  PHOTO RE-CATEGORIZATION SCRIPT")
    print("=======================================\n")
    
    print("Loading AI Face Model (buffalo_l) - Please wait...")
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("AI Model loaded successfully!\n")

    print("Step 1: Checking for existing progress...")
    # (Removed the global folder wipe so we don't lose the progress of the 319 photos)

    photos = Photo.objects.all()
    total = photos.count()
    print(f"Step 2: Processing {total} photos...\n")
    
    success_count = 0
    fail_count = 0

    for i, photo in enumerate(photos):
        sys.stdout.write(f"[{i+1}/{total}] Processing {photo.original_filename}... ")
        sys.stdout.flush()
        
        # If it already has faces from the previous run, skip downloading it again!
        if photo.faces.exists():
            # Just re-categorize it to be safe, but skip the heavy AI extraction
            categorize_photo(photo)
            photo.refresh_from_db()
            folder_display = photo.folder if photo.folder else "None"
            print(f"SKIPPED (Already processed) -> Folder: '{folder_display}'")
            success_count += 1
            continue
            
        # Clear any corrupted data from an interrupted run
        photo.faces.all().delete()
        
        try:
            # Download image with a 15-second timeout
            req = urllib.request.urlopen(photo.cloudinary_url or photo.secure_url, timeout=15)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, -1)
        except Exception as e:
            print(f"FAILED (Download error: {e})")
            fail_count += 1
            continue
            
        if img is None:
            print("FAILED (Corrupt image data)")
            fail_count += 1
            continue
            
        try:
            # Extract faces
            faces = app.get(img)
            for face in faces:
                Face.objects.create(
                    photo=photo,
                    embedding=face.embedding.tolist(),
                    x=face.bbox[0],
                    y=face.bbox[1],
                    width=face.bbox[2] - face.bbox[0],
                    height=face.bbox[3] - face.bbox[1],
                    detection_confidence=face.det_score
                )
            
            # Apply strict categorization logic
            categorize_photo(photo)
            
            # Re-fetch photo to get updated folder
            photo.refresh_from_db()
            folder_display = photo.folder if photo.folder else "None"
            print(f"DONE -> Folder: '{folder_display}'")
            success_count += 1
            
        except Exception as e:
            print(f"FAILED (AI Processing error: {e})")
            fail_count += 1

    print("\n=======================================")
    print("  FINISHED!")
    print(f"  Successfully processed: {success_count}")
    print(f"  Failed to process: {fail_count}")
    print("=======================================")

if __name__ == "__main__":
    main()

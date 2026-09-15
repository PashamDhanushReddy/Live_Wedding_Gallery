import os
import sys
import django
import cv2
import numpy as np
from insightface.app import FaceAnalysis

sys.path.insert(0, os.path.abspath('backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from photos.models import Photo
from faces.models import Face

app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

def index_faces():
    photos = Photo.objects.all()
    print(f"Indexing faces for {photos.count()} photos...")
    for photo in photos:
        # Check if faces already exist
        if Face.objects.filter(photo=photo).exists():
            print(f"Skipping {photo.original_filename} - faces already indexed")
            continue
            
        file_path = os.path.join('uploader', 'WATCH_FOLDER', photo.original_filename)
        if not os.path.exists(file_path):
            print(f"File not found locally: {file_path}")
            continue
            
        img = cv2.imread(file_path)
        if img is None:
            continue
            
        faces = app.get(img)
        print(f"Found {len(faces)} faces in {photo.original_filename}")
        
        for face in faces:
            embedding = face.embedding.tolist()
            bbox = face.bbox.tolist() # [x1, y1, x2, y2]
            Face.objects.create(
                photo=photo,
                embedding=embedding,
                x=float(bbox[0]),
                y=float(bbox[1]),
                width=float(bbox[2] - bbox[0]),
                height=float(bbox[3] - bbox[1]),
                detection_confidence=float(face.det_score)
            )

if __name__ == "__main__":
    index_faces()

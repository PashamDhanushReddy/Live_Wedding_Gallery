import cv2
import json
import logging
import threading
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

# Initialize the FaceAnalysis app using the 'buffalo_l' model which includes
# detection and recognition. We specify ctx_id=0 to try GPU if available, else CPU.
try:
    print("Initializing InsightFace model (this may take a moment to load into memory...)")
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=0, det_size=(640, 640))
except Exception as e:
    print(f"Failed to initialize FaceAnalysis: {e}")
    app = None

# ONNXRuntime is not thread-safe for concurrent inference on the same session
face_lock = threading.Lock()

def analyze_faces(file_path):
    """
    Analyzes an image and returns a list of faces with bounding boxes,
    confidence, and 512-d embeddings.
    """
    if app is None:
        return []

    try:
        # InsightFace expects a BGR image, which is the default for cv2.imread
        img = cv2.imread(file_path)
        if img is None:
            print(f"Failed to read image: {file_path}")
            return []

        with face_lock:
            faces = app.get(img)
            
        faces_data = []

        for face in faces:
            # bbox is [x1, y1, x2, y2]
            bbox = face.bbox.tolist()
            # embedding is a 512 float array
            embedding = face.embedding.tolist()
            # detection confidence
            confidence = float(face.det_score)

            # To avoid saving low-quality/false-positive faces
            if confidence > 0.5:
                faces_data.append({
                    'bbox': bbox,
                    'confidence': confidence,
                    'embedding': embedding
                })
        
        print(f"Found {len(faces_data)} faces in {file_path}.")
        return faces_data
    except Exception as e:
        print(f"Error analyzing faces for {file_path}: {e}")
        return []

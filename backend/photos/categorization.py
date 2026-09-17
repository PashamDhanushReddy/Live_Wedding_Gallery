import numpy as np

def cosine_distance(vec1, vec2):
    """Calculate the cosine distance between two vectors."""
    if not vec1 or not vec2:
        return 1.0
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    # Cosine similarity is dot product divided by norms
    # Distance is 1 - similarity
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    similarity = np.dot(v1, v2) / (norm1 * norm2)
    return 1.0 - similarity

def categorize_photo(photo):
    """
    Categorize a photo based on its faces and the wedding's reference embeddings.
    Updates the photo.folder field and saves the photo if categorized.
    """
    wedding = photo.wedding
    bride_embedding = wedding.bride_embedding
    groom_embedding = wedding.groom_embedding
    
    # If no references are set, we can't categorize
    if not bride_embedding and not groom_embedding:
        return False
        
    has_bride = False
    has_groom = False
    
    # Threshold for matching a face (lower is stricter)
    THRESHOLD = 0.45
    
    faces = photo.faces.all()
    
    # Calculate a proxy for face size to filter out small background faces
    # Assuming a typical photo, faces > 100x100 pixels are prominent, or just take the top 2-3 largest faces.
    # Let's sort faces by size (width * height) descending.
    sorted_faces = sorted(faces, key=lambda f: f.width * f.height, reverse=True)
    
    # A prominent face is one that is at least 15% the size of the largest face in the photo,
    # or just rely on a strict count of the top 5 largest faces to avoid tiny background blurs.
    prominent_faces = []
    if sorted_faces:
        max_area = sorted_faces[0].width * sorted_faces[0].height
        prominent_faces = [f for f in sorted_faces if (f.width * f.height) >= max_area * 0.15]
    
    total_prominent = len(prominent_faces)
    
    # We only check matches against the prominent faces
    for face in prominent_faces:
        embedding = face.embedding
        if not embedding:
            continue
            
        if bride_embedding:
            dist_bride = cosine_distance(embedding, bride_embedding)
            if dist_bride < THRESHOLD:
                has_bride = True
                
        if groom_embedding:
            dist_groom = cosine_distance(embedding, groom_embedding)
            if dist_groom < THRESHOLD:
                has_groom = True
                
    # Determine the folder based on matches and PROMINENT face counts
    new_folder = None
    if has_bride and has_groom and total_prominent == 2:
        new_folder = "Bride and Groom"
    elif has_bride and not has_groom and total_prominent == 1:
        new_folder = "Bride"
    elif has_groom and not has_bride and total_prominent == 1:
        new_folder = "Groom"
        
    # If the photo was in an AI folder but no longer matches, clear the folder
    if new_folder is None and photo.folder in ["Bride", "Groom", "Bride and Groom"]:
        photo.folder = ""
        photo.save(update_fields=['folder'])
        return True
        
    if new_folder and photo.folder != new_folder:
        photo.folder = new_folder
        photo.save(update_fields=['folder'])
        return True
        
    return False

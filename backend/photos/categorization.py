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
    
    # Threshold for matching a face (lower is stricter, usually 0.4 to 0.6 for insightface)
    THRESHOLD = 0.5
    
    # Check all faces in the photo
    for face in photo.faces.all():
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
                
    # Determine the folder based on matches
    new_folder = None
    if has_bride and has_groom:
        new_folder = "Bride and Groom"
    elif has_bride:
        new_folder = "Bride"
    elif has_groom:
        new_folder = "Groom"
        
    if new_folder and photo.folder != new_folder:
        photo.folder = new_folder
        photo.save(update_fields=['folder'])
        return True
        
    return False

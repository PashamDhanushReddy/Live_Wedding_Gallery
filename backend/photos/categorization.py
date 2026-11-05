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
    Updates the photo.ai_category field (and photo.folder only if unassigned).
    Preserves photographer-assigned event folders (Haldi, Wedding Day, etc.).
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
                
    # Determine the AI category based on matches and PROMINENT face counts
    new_ai_category = None
    if has_bride and has_groom and total_prominent == 2:
        new_ai_category = "Bride and Groom"
    elif has_bride and not has_groom and total_prominent == 1:
        new_ai_category = "Bride"
    elif has_groom and not has_bride and total_prominent == 1:
        new_ai_category = "Groom"
        
    changed = False
    update_fields = []

    # 1. Update ai_category
    current_ai_cat = getattr(photo, 'ai_category', None)
    if current_ai_cat != new_ai_category:
        photo.ai_category = new_ai_category
        changed = True
        update_fields.append('ai_category')

    # 2. Update folder:
    # If photo already belongs to an event folder (Haldi, Wedding Day, Pre-wedding Shoot, etc.),
    # NEVER overwrite it! Keep the photographer's explicit folder assignment intact.
    # Only assign AI folder if the folder is empty, "Uncategorized", or was previously an AI category.
    is_event_folder = bool(
        photo.folder and photo.folder.strip() not in [
            "Bride", "Groom", "Bride and Groom", "Uncategorized", ""
        ]
    )
    if not is_event_folder:
        target_folder = new_ai_category or "Uncategorized"
        if photo.folder != target_folder:
            photo.folder = target_folder
            changed = True
            update_fields.append('folder')

    if changed and update_fields:
        photo.save(update_fields=update_fields)
        return True
        
    return False

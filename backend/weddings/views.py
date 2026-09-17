from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Wedding
from .serializers import WeddingSerializer
from photos.models import Photo
from photos.serializers import PhotoSerializer

class WeddingListCreateView(generics.ListCreateAPIView):
    queryset = Wedding.objects.all().order_by('-created_at')
    serializer_class = WeddingSerializer

class PhotographerLoginView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'status': 'success', 'token': token.key})
        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

class WeddingDetailView(generics.RetrieveAPIView):
    queryset = Wedding.objects.filter(is_active=True)
    serializer_class = WeddingSerializer
    lookup_field = 'slug'

class WeddingPhotosView(generics.ListAPIView):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        return Photo.objects.filter(wedding=wedding, processing_status='COMPLETED').order_by('-created_at')

class PhotoSyncView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        data = request.data
        
        # In production, check API_KEY here to authorize uploader script
        
        # 1. Save Photo
        from photos.models import Photo
        from faces.models import Face
        from django.db import transaction
        
        try:
            with transaction.atomic():
                photo, created = Photo.objects.get_or_create(
                    wedding=wedding,
                    checksum=data.get('checksum'),
                    defaults={
                        'original_filename': data.get('original_filename'),
                        'cloudinary_public_id': data.get('cloudinary_public_id'),
                        'cloudinary_url': data.get('cloudinary_url', ''),
                        'secure_url': data.get('secure_url', ''),
                        'thumbnail_url': data.get('thumbnail_url', ''),
                        'width': data.get('width'),
                        'height': data.get('height'),
                        'file_size': data.get('file_size'),
                        'processing_status': 'COMPLETED'
                    }
                )
                
                if not created:
                    return Response({"status": "duplicate", "photo_id": photo.id}, status=200)
                
                # 2. Save Faces with pgvector embeddings
                faces_data = data.get('faces', [])
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
                    
                # 2.5 Categorize photo
                from photos.categorization import categorize_photo
                categorize_photo(photo)
                    
                # 3. Broadcast to WebSockets
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                
                channel_layer = get_channel_layer()
                
                # We need to serialize the photo to send it
                from photos.serializers import PhotoSerializer
                photo_data = PhotoSerializer(photo).data
                
                async_to_sync(channel_layer.group_send)(
                    f'wedding_{slug}',
                    {
                        'type': 'new_photo',
                        'photo': photo_data
                    }
                )
                    
            return Response({"status": "success", "photo_id": photo.id}, status=201)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=400)



class FaceSearchView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        
        # 1. Get the uploaded image
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)
            
        file_obj = request.FILES['file']
        
        # 2. Extract embedding using InsightFace
        try:
            import cv2
            import numpy as np
            from photos.views import get_face_app, _face_lock
            
            # Read image from memory
            file_bytes = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            app = get_face_app()
            
            with _face_lock:
                faces = app.get(img)
            if not faces:
                return Response({"error": "No faces found in the image."}, status=400)
                
            # Assume the largest/most confident face is the one to search for
            target_embedding = faces[0].embedding.tolist()
            
        except Exception as e:
            return Response({"error": f"Failed to process face: {str(e)}"}, status=500)
            
        # 3. Perform Vector Search using pgvector
        from photos.models import Photo
        from faces.models import Face
        from pgvector.django import CosineDistance
        
        # We query Faces that belong to this wedding
        # Order by CosineDistance and filter matches (distance < threshold e.g. 0.4)
        matched_faces = Face.objects.filter(
            photo__wedding=wedding
        ).annotate(
            distance=CosineDistance('embedding', target_embedding)
        ).filter(
            distance__lt=0.5
        ).order_by('distance')
        
        # Get unique photos
        photo_ids = matched_faces.values_list('photo_id', flat=True).distinct()
        
        # We need to preserve order, or just return them
        # Let's return the photos
        photos = Photo.objects.filter(id__in=photo_ids).order_by('-created_at')
        
        from photos.serializers import PhotoSerializer
        serializer = PhotoSerializer(photos, many=True)
        
        return Response({
            "status": "success",
            "matches_count": photos.count(),
            "photos": serializer.data
        }, status=200)

class SetReferenceFaceView(APIView):
    def post(self, request, slug):
        wedding = get_object_or_404(Wedding, slug=slug, is_active=True)
        role = request.data.get('role') # 'bride' or 'groom'
        
        if role not in ['bride', 'groom']:
            return Response({"error": "Invalid role. Must be 'bride' or 'groom'."}, status=400)
            
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)
            
        file_obj = request.FILES['file']
        
        try:
            import cv2
            import numpy as np
            from photos.views import get_face_app, _face_lock
            
            # Read image from memory
            file_bytes = np.asarray(bytearray(file_obj.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            app = get_face_app()
            
            with _face_lock:
                faces = app.get(img)
                
            if not faces:
                return Response({"error": "No faces found in the image."}, status=400)
                
            # Assume the largest/most confident face is the reference
            target_embedding = faces[0].embedding.tolist()
            
            if role == 'bride':
                wedding.bride_embedding = target_embedding
            else:
                wedding.groom_embedding = target_embedding
                
            wedding.save()
            
            return Response({"status": "success", "message": f"{role.capitalize()} reference face set successfully."})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Failed to process face: {str(e)}"}, status=500)
